"""Utility modules for UUID classification.

This package contains helper utilities including BLE pattern matching
and other classification support functions.
"""

from uuid_classifier.utils.ble_patterns import (
    AUTHORITATIVE_DOMAINS,
    BLUETOOTH_SIG_BASE_SUFFIX,
    EDDYSTONE_INDICATORS,
    IBEACON_INDICATORS,
    KNOWN_BLE_SERVICES,
    VENDOR_INDICATORS,
    KnownService,
    extract_short_uuid,
    get_known_service,
    is_authoritative_source,
    is_bluetooth_sig_uuid,
)

__all__ = [
    "AUTHORITATIVE_DOMAINS",
    "BLUETOOTH_SIG_BASE_SUFFIX",
    "EDDYSTONE_INDICATORS",
    "IBEACON_INDICATORS",
    "KNOWN_BLE_SERVICES",
    "VENDOR_INDICATORS",
    "KnownService",
    "extract_short_uuid",
    "get_known_service",
    "is_authoritative_source",
    "is_bluetooth_sig_uuid",
]
