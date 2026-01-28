"""BLE (Bluetooth Low Energy) UUID patterns and known services.

This module contains patterns for identifying standard BLE services,
vendor-specific UUIDs, and other known Bluetooth identifiers.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class KnownService:
    """Represents a known BLE service."""

    uuid_short: str  # Short UUID (e.g., "180D")
    name: str
    description: str


# Bluetooth SIG Base UUID pattern
# Standard BLE services use the format: 0000xxxx-0000-1000-8000-00805f9b34fb
BLUETOOTH_SIG_BASE_SUFFIX = "-0000-1000-8000-00805f9b34fb"

# Pattern to extract short UUID from full Bluetooth SIG UUID
# Matches UUIDs like 0000180d-0000-1000-8000-00805f9b34fb -> extracts "180d"
BLUETOOTH_SIG_UUID_PATTERN = re.compile(
    r"^0000([0-9a-f]{4})-0000-1000-8000-00805f9b34fb$",
    re.IGNORECASE,
)

# Known Bluetooth SIG assigned services
# Reference: https://www.bluetooth.com/specifications/assigned-numbers/
KNOWN_BLE_SERVICES: dict[str, KnownService] = {
    "1800": KnownService(
        uuid_short="1800",
        name="Generic Access",
        description="Generic Access Profile service for device name and appearance",
    ),
    "1801": KnownService(
        uuid_short="1801",
        name="Generic Attribute",
        description="Generic Attribute Profile service for service discovery",
    ),
    "1802": KnownService(
        uuid_short="1802",
        name="Immediate Alert",
        description="Immediate Alert service for alerting devices",
    ),
    "1803": KnownService(
        uuid_short="1803",
        name="Link Loss",
        description="Link Loss service for proximity detection",
    ),
    "1804": KnownService(
        uuid_short="1804",
        name="Tx Power",
        description="Tx Power service for transmission power reporting",
    ),
    "1805": KnownService(
        uuid_short="1805",
        name="Current Time",
        description="Current Time service for time synchronization",
    ),
    "1806": KnownService(
        uuid_short="1806",
        name="Reference Time Update",
        description="Reference Time Update service for time calibration",
    ),
    "1807": KnownService(
        uuid_short="1807",
        name="Next DST Change",
        description="Next DST Change service for daylight saving time updates",
    ),
    "1808": KnownService(
        uuid_short="1808",
        name="Glucose",
        description="Glucose service for blood glucose monitoring",
    ),
    "1809": KnownService(
        uuid_short="1809",
        name="Health Thermometer",
        description="Health Thermometer service for body temperature measurement",
    ),
    "180a": KnownService(
        uuid_short="180A",
        name="Device Information",
        description="Device Information service for manufacturer and model data",
    ),
    "180d": KnownService(
        uuid_short="180D",
        name="Heart Rate",
        description="Heart Rate service for heart rate monitoring",
    ),
    "180e": KnownService(
        uuid_short="180E",
        name="Phone Alert Status",
        description="Phone Alert Status service for phone alerts",
    ),
    "180f": KnownService(
        uuid_short="180F",
        name="Battery Service",
        description="Battery Service for battery level reporting",
    ),
    "1810": KnownService(
        uuid_short="1810",
        name="Blood Pressure",
        description="Blood Pressure service for blood pressure monitoring",
    ),
    "1811": KnownService(
        uuid_short="1811",
        name="Alert Notification",
        description="Alert Notification service for push notifications",
    ),
    "1812": KnownService(
        uuid_short="1812",
        name="Human Interface Device",
        description="Human Interface Device service for HID over GATT",
    ),
    "1813": KnownService(
        uuid_short="1813",
        name="Scan Parameters",
        description="Scan Parameters service for scan configuration",
    ),
    "1814": KnownService(
        uuid_short="1814",
        name="Running Speed and Cadence",
        description="Running Speed and Cadence service for fitness tracking",
    ),
    "1816": KnownService(
        uuid_short="1816",
        name="Cycling Speed and Cadence",
        description="Cycling Speed and Cadence service for cycling fitness",
    ),
    "1818": KnownService(
        uuid_short="1818",
        name="Cycling Power",
        description="Cycling Power service for power meters",
    ),
    "1819": KnownService(
        uuid_short="1819",
        name="Location and Navigation",
        description="Location and Navigation service for GPS data",
    ),
    "181a": KnownService(
        uuid_short="181A",
        name="Environmental Sensing",
        description="Environmental Sensing service for environmental data",
    ),
    "181c": KnownService(
        uuid_short="181C",
        name="User Data",
        description="User Data service for user profile information",
    ),
    "181d": KnownService(
        uuid_short="181D",
        name="Weight Scale",
        description="Weight Scale service for body weight measurement",
    ),
    "181e": KnownService(
        uuid_short="181E",
        name="Bond Management",
        description="Bond Management service for pairing management",
    ),
    "181f": KnownService(
        uuid_short="181F",
        name="Continuous Glucose Monitoring",
        description="Continuous Glucose Monitoring service for CGM devices",
    ),
    "1820": KnownService(
        uuid_short="1820",
        name="Internet Protocol Support",
        description="Internet Protocol Support service for IP connectivity",
    ),
    "1821": KnownService(
        uuid_short="1821",
        name="Indoor Positioning",
        description="Indoor Positioning service for indoor location",
    ),
    "1822": KnownService(
        uuid_short="1822",
        name="Pulse Oximeter",
        description="Pulse Oximeter service for SpO2 measurement",
    ),
    "1823": KnownService(
        uuid_short="1823",
        name="HTTP Proxy",
        description="HTTP Proxy service for web access via BLE",
    ),
    "1824": KnownService(
        uuid_short="1824",
        name="Transport Discovery",
        description="Transport Discovery service for transport discovery",
    ),
    "1825": KnownService(
        uuid_short="1825",
        name="Object Transfer",
        description="Object Transfer service for file transfer",
    ),
    "1826": KnownService(
        uuid_short="1826",
        name="Fitness Machine",
        description="Fitness Machine service for fitness equipment",
    ),
    "1827": KnownService(
        uuid_short="1827",
        name="Mesh Provisioning",
        description="Mesh Provisioning service for Bluetooth Mesh",
    ),
    "1828": KnownService(
        uuid_short="1828",
        name="Mesh Proxy",
        description="Mesh Proxy service for Bluetooth Mesh",
    ),
}

# Vendor indicators to detect in search results
VENDOR_INDICATORS: list[str] = [
    "apple",
    "samsung",
    "google",
    "fitbit",
    "garmin",
    "nordic",
    "nordic semiconductor",
    "texas instruments",
    "silicon labs",
    "espressif",
    "qualcomm",
    "broadcom",
    "xiaomi",
    "huawei",
    "microsoft",
    "amazon",
    "nrf",  # Nordic nRF
]

# iBeacon detection patterns
IBEACON_INDICATORS: list[str] = [
    "ibeacon",
    "i-beacon",
    "apple beacon",
    "proximity uuid",
]

# Eddystone detection patterns
EDDYSTONE_INDICATORS: list[str] = [
    "eddystone",
    "google beacon",
    "eddystone-uid",
    "eddystone-url",
    "eddystone-tlm",
    "eddystone-eid",
]

# Official/authoritative sources that increase confidence
AUTHORITATIVE_DOMAINS: list[str] = [
    "bluetooth.com",
    "bluetooth.org",
    "developer.apple.com",
    "developer.android.com",
    "developer.nordicsemi.com",
    "infocenter.nordicsemi.com",
    "ti.com",
    "silabs.com",
]


def is_bluetooth_sig_uuid(uuid: str) -> bool:
    """Check if a UUID follows the Bluetooth SIG base UUID pattern.

    Args:
        uuid: The UUID string to check (lowercase with hyphens).

    Returns:
        True if UUID matches Bluetooth SIG pattern.
    """
    return BLUETOOTH_SIG_UUID_PATTERN.match(uuid) is not None


def extract_short_uuid(uuid: str) -> str | None:
    """Extract the short UUID from a Bluetooth SIG UUID.

    Args:
        uuid: The full UUID string (lowercase with hyphens).

    Returns:
        The 4-character short UUID, or None if not a Bluetooth SIG UUID.
    """
    match = BLUETOOTH_SIG_UUID_PATTERN.match(uuid)
    if match:
        return match.group(1).lower()
    return None


def get_known_service(uuid: str) -> KnownService | None:
    """Get known service information for a UUID.

    Args:
        uuid: The UUID string (lowercase with hyphens).

    Returns:
        KnownService if found, None otherwise.
    """
    short_uuid = extract_short_uuid(uuid)
    if short_uuid:
        return KNOWN_BLE_SERVICES.get(short_uuid)
    return None


def is_authoritative_source(url: str) -> bool:
    """Check if a URL is from an authoritative Bluetooth-related domain.

    Args:
        url: The URL to check.

    Returns:
        True if URL is from an authoritative domain.
    """
    url_lower = url.lower()
    return any(domain in url_lower for domain in AUTHORITATIVE_DOMAINS)
