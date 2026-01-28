"""Classifier service for heuristic-based UUID classification.

This service analyzes search results and applies heuristics to compile
structured classification records for UUIDs, with emphasis on BLE services.
"""

import logging
import re
from collections import Counter
from datetime import UTC, datetime

from pydantic import HttpUrl

from uuid_classifier.schemas.classification import (
    ClassificationCreate,
    ClassificationType,
    ConfidenceLevel,
    SearchResult,
    SourceInfo,
)
from uuid_classifier.utils.ble_patterns import (
    EDDYSTONE_INDICATORS,
    IBEACON_INDICATORS,
    VENDOR_INDICATORS,
    KnownService,
    get_known_service,
    is_authoritative_source,
    is_bluetooth_sig_uuid,
)

logger = logging.getLogger(__name__)


class ClassifierService:
    """Service for classifying UUIDs based on search results.

    This service uses heuristic analysis of search results to determine
    the type, name, and confidence of a UUID classification.

    The classification logic:
    1. Check if UUID matches known Bluetooth SIG patterns
    2. Analyze search results for iBeacon/Eddystone indicators
    3. Detect vendor-specific patterns
    4. Extract names from consistent search results
    5. Calculate confidence based on result agreement and source authority
    """

    # Patterns for extracting service names from text
    NAME_EXTRACTION_PATTERNS: list[re.Pattern[str]] = [
        # "Heart Rate Service" or "Heart Rate"
        re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Service|Profile)", re.IGNORECASE),
        # "service name: Heart Rate"
        re.compile(r"(?:service|profile|name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.IGNORECASE),
        # Nordic UART Service
        re.compile(r"(Nordic\s+UART\s+Service|NUS)", re.IGNORECASE),
        # UUID names like "Battery Level" before UUID
        re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:UUID|0x[0-9A-Fa-f]+)", re.IGNORECASE),
    ]

    async def classify(
        self,
        uuid: str,
        search_results: list[SearchResult],
    ) -> ClassificationCreate:
        """Analyze search results and produce a classification.

        Args:
            uuid: The UUID being classified (normalized format).
            search_results: List of search results from the search service.

        Returns:
            ClassificationCreate with the compiled classification data.
        """
        logger.info("Classifying UUID: %s with %d search results", uuid, len(search_results))

        # First, check for known Bluetooth SIG service
        known_service = get_known_service(uuid)
        if known_service:
            logger.info("UUID matches known BLE service: %s", known_service.name)
            return self._create_known_service_classification(
                uuid, known_service, search_results
            )

        # Handle empty search results
        if not search_results:
            logger.info("No search results - returning Unknown classification")
            return self._create_unknown_classification(uuid)

        # Analyze search results for classification
        classification_type = self._detect_type(uuid, search_results)
        name = self._extract_name(search_results)
        description = self._generate_description(name, classification_type, search_results)
        confidence = self._calculate_confidence(search_results, name)
        sources = self._build_sources(search_results)

        logger.info(
            "Classification complete: type=%s, name=%s, confidence=%s",
            classification_type.value,
            name,
            confidence.value,
        )

        return ClassificationCreate(
            uuid=uuid,
            name=name,
            type=classification_type,
            description=description,
            sources=sources,
            confidence=confidence,
            searched_at=datetime.now(UTC),
        )

    def _create_known_service_classification(
        self,
        uuid: str,
        known_service: KnownService,
        search_results: list[SearchResult],
    ) -> ClassificationCreate:
        """Create classification for a known Bluetooth SIG service.

        Args:
            uuid: The UUID being classified.
            known_service: The known service information.
            search_results: Search results (used for sources).

        Returns:
            ClassificationCreate for the known service.
        """
        service = known_service

        return ClassificationCreate(
            uuid=uuid,
            name=service.name,
            type=ClassificationType.STANDARD_BLE_SERVICE,
            description=service.description,
            sources=self._build_sources(search_results),
            confidence=ConfidenceLevel.HIGH,
            searched_at=datetime.now(UTC),
        )

    def _create_unknown_classification(self, uuid: str) -> ClassificationCreate:
        """Create an Unknown classification when no information is found.

        Args:
            uuid: The UUID being classified.

        Returns:
            ClassificationCreate with Unknown type and low confidence.
        """
        return ClassificationCreate(
            uuid=uuid,
            name="Unknown",
            type=ClassificationType.UNKNOWN,
            description="Unable to identify this UUID. No information found in search results.",
            sources=[],
            confidence=ConfidenceLevel.LOW,
            searched_at=datetime.now(UTC),
        )

    def _detect_type(
        self,
        uuid: str,
        search_results: list[SearchResult],
    ) -> ClassificationType:
        """Detect the classification type based on UUID and search results.

        Args:
            uuid: The UUID being classified.
            search_results: List of search results to analyze.

        Returns:
            The detected ClassificationType.
        """
        # Combine all text from results for analysis
        all_text = self._combine_result_text(search_results).lower()

        # Check for iBeacon indicators
        if any(indicator in all_text for indicator in IBEACON_INDICATORS):
            logger.debug("Detected iBeacon indicators in search results")
            return ClassificationType.APPLE_IBEACON

        # Check for Eddystone indicators
        if any(indicator in all_text for indicator in EDDYSTONE_INDICATORS):
            logger.debug("Detected Eddystone indicators in search results")
            return ClassificationType.GOOGLE_EDDYSTONE

        # Check if it's a Bluetooth SIG format UUID (even if not in known list)
        if is_bluetooth_sig_uuid(uuid):
            logger.debug("UUID matches Bluetooth SIG format")
            return ClassificationType.STANDARD_BLE_SERVICE

        # Check for vendor-specific indicators
        if any(vendor in all_text for vendor in VENDOR_INDICATORS):
            logger.debug("Detected vendor-specific indicators in search results")
            return ClassificationType.VENDOR_SPECIFIC

        # Check for generic BLE/GATT indicators
        ble_indicators = ["bluetooth", "ble", "gatt", "service", "characteristic"]
        if any(indicator in all_text for indicator in ble_indicators):
            logger.debug("Detected generic BLE indicators - classifying as Custom Service")
            return ClassificationType.CUSTOM_SERVICE

        logger.debug("No clear type indicators found - classifying as Unknown")
        return ClassificationType.UNKNOWN

    def _extract_name(
        self,
        search_results: list[SearchResult],
    ) -> str:
        """Extract the most likely name from search results.

        Uses frequency analysis to find the most commonly mentioned name
        across search results.

        Args:
            search_results: List of search results to analyze.

        Returns:
            The extracted name or "Unknown" if none found.
        """
        if not search_results:
            return "Unknown"

        # Collect potential names from all results
        potential_names: list[str] = []

        for result in search_results:
            # Try extracting from title and snippet
            for text in [result.title, result.snippet]:
                for pattern in self.NAME_EXTRACTION_PATTERNS:
                    matches = pattern.findall(text)
                    potential_names.extend(matches)

        if not potential_names:
            # Fallback: Try to extract from first result title
            if search_results:
                first_title = search_results[0].title
                # Remove common suffixes and clean up
                name = self._clean_title_for_name(first_title)
                if name and name.lower() != "unknown":
                    return name
            return "Unknown"

        # Normalize names for counting (case-insensitive)
        normalized_names: Counter[str] = Counter()
        for name in potential_names:
            # Skip very short names or generic terms
            if len(name) < 3 or name.lower() in {"the", "and", "for", "ble", "uuid"}:
                continue
            normalized_names[name.strip()] += 1

        if not normalized_names:
            return "Unknown"

        # Return the most common name
        most_common = normalized_names.most_common(1)[0][0]
        return most_common

    def _clean_title_for_name(self, title: str) -> str:
        """Clean a search result title to extract a potential name.

        Args:
            title: The search result title.

        Returns:
            Cleaned name string.
        """
        # Remove common suffixes
        suffixes_to_remove = [
            " - Bluetooth SIG",
            " - Bluetooth",
            " | Bluetooth",
            " - Nordic",
            " - Apple",
            " Service UUID",
            " UUID",
        ]
        result = title
        for suffix in suffixes_to_remove:
            if result.lower().endswith(suffix.lower()):
                result = result[: -len(suffix)]

        # Take first part if there's a separator
        for separator in [" - ", " | ", " : "]:
            if separator in result:
                result = result.split(separator)[0]

        return result.strip()

    def _generate_description(
        self,
        name: str,
        classification_type: ClassificationType,
        search_results: list[SearchResult],
    ) -> str:
        """Generate a description based on classification and results.

        Args:
            name: The extracted name.
            classification_type: The classification type.
            search_results: Search results for context.

        Returns:
            Generated description string.
        """
        type_descriptions = {
            ClassificationType.STANDARD_BLE_SERVICE: f"Bluetooth SIG standardized {name} service",
            ClassificationType.VENDOR_SPECIFIC: f"Vendor-specific {name} service",
            ClassificationType.APPLE_IBEACON: f"Apple iBeacon {name}",
            ClassificationType.GOOGLE_EDDYSTONE: f"Google Eddystone {name}",
            ClassificationType.CUSTOM_SERVICE: f"Custom BLE {name} service",
            ClassificationType.UNKNOWN: "Unable to identify this UUID",
        }

        base_description = type_descriptions.get(
            classification_type,
            f"{name} service",
        )

        # Try to add context from the best search result snippet
        if search_results:
            # Find the best snippet (prefer authoritative sources)
            best_snippet = None
            for result in search_results:
                if result.snippet:
                    if is_authoritative_source(result.url):
                        best_snippet = result.snippet
                        break
                    elif best_snippet is None:
                        best_snippet = result.snippet

            if best_snippet and len(best_snippet) > 20:
                # Truncate long snippets
                if len(best_snippet) > 200:
                    best_snippet = best_snippet[:197] + "..."
                return f"{base_description}. {best_snippet}"

        return base_description

    def _calculate_confidence(
        self,
        search_results: list[SearchResult],
        extracted_name: str,
    ) -> ConfidenceLevel:
        """Calculate confidence level based on result agreement and sources.

        Confidence is HIGH when:
        - 3+ results mention the same name
        - At least one authoritative source is present

        Confidence is MEDIUM when:
        - 2 results agree on name
        - OR single authoritative source

        Confidence is LOW when:
        - Conflicting or sparse information
        - No authoritative sources

        Args:
            search_results: Search results to analyze.
            extracted_name: The extracted name for comparison.

        Returns:
            The calculated ConfidenceLevel.
        """
        if not search_results or extracted_name == "Unknown":
            return ConfidenceLevel.LOW

        # Count how many results mention the extracted name
        name_lower = extracted_name.lower()
        name_mentions = 0
        authoritative_count = 0

        for result in search_results:
            combined_text = f"{result.title} {result.snippet}".lower()
            if name_lower in combined_text:
                name_mentions += 1
            if is_authoritative_source(result.url):
                authoritative_count += 1

        # Determine confidence
        if name_mentions >= 3 and authoritative_count >= 1:
            return ConfidenceLevel.HIGH
        elif name_mentions >= 2 or authoritative_count >= 1:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _build_sources(self, search_results: list[SearchResult]) -> list[SourceInfo]:
        """Build source information list from search results.

        Args:
            search_results: Search results to convert.

        Returns:
            List of SourceInfo objects.
        """
        sources: list[SourceInfo] = []

        for result in search_results[:5]:  # Limit to top 5 sources
            try:
                source = SourceInfo(
                    title=result.title,
                    url=HttpUrl(result.url),
                    snippet=result.snippet or "No snippet available",
                )
                sources.append(source)
            except ValueError as e:
                logger.warning("Skipping invalid source URL %s: %s", result.url, e)
                continue

        return sources

    def _combine_result_text(self, search_results: list[SearchResult]) -> str:
        """Combine all text from search results for analysis.

        Args:
            search_results: Search results to combine.

        Returns:
            Combined text string.
        """
        parts: list[str] = []
        for result in search_results:
            parts.append(result.title)
            if result.snippet:
                parts.append(result.snippet)
        return " ".join(parts)
