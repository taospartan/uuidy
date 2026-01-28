"""Mock SerpAPI responses for testing.

These mock responses simulate real SerpAPI Google search results
without making actual API calls. Used for unit and integration tests.
"""

from typing import Any

# Standard Heart Rate Service UUID response
HEART_RATE_SERVICE_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "abc123",
        "status": "Success",
        "json_endpoint": "https://serpapi.com/searches/abc123.json",
        "created_at": "2026-01-28 10:00:00 UTC",
        "processed_at": "2026-01-28 10:00:01 UTC",
        "google_url": "https://www.google.com/search?q=%220000180d-0000-1000-8000-00805f9b34fb%22",
        "raw_html_file": "https://serpapi.com/searches/abc123.html",
        "total_time_taken": 1.23,
    },
    "search_parameters": {
        "engine": "google",
        "q": '"0000180d-0000-1000-8000-00805f9b34fb" bluetooth OR BLE OR service OR GATT OR beacon',
        "google_domain": "google.com",
        "hl": "en",
        "gl": "us",
    },
    "organic_results": [
        {
            "position": 1,
            "title": "Heart Rate Service - Bluetooth SIG",
            "link": "https://www.bluetooth.com/specifications/gatt/services/",
            "displayed_link": "www.bluetooth.com › specifications › gatt",
            "snippet": "The Heart Rate Service exposes heart rate and other data from a Heart Rate Sensor intended for fitness applications. UUID: 0x180D",
            "snippet_highlighted_words": ["Heart Rate Service", "0x180D"],
        },
        {
            "position": 2,
            "title": "GATT Specifications | Bluetooth® Technology Website",
            "link": "https://www.bluetooth.com/specifications/gatt/",
            "displayed_link": "www.bluetooth.com › specifications › gatt",
            "snippet": "GATT Services and Characteristics. Heart Rate Service (0x180D) - Exposes heart rate data from sensors.",
            "snippet_highlighted_words": ["Heart Rate Service", "0x180D"],
        },
        {
            "position": 3,
            "title": "Bluetooth Low Energy Heart Rate Service - Nordic Semiconductor",
            "link": "https://infocenter.nordicsemi.com/topic/sdk_nrf5_v17.1.0/ble_sdk_app_hrs.html",
            "displayed_link": "infocenter.nordicsemi.com › topic",
            "snippet": "The Heart Rate Service (HRS) with UUID 0x180D is a standardized BLE service for heart rate monitors and fitness devices.",
            "snippet_highlighted_words": ["Heart Rate Service", "HRS", "0x180D"],
        },
        {
            "position": 4,
            "title": "Understanding BLE GATT Services and Characteristics",
            "link": "https://developer.apple.com/documentation/corebluetooth",
            "displayed_link": "developer.apple.com › documentation",
            "snippet": "Bluetooth GATT defines standardized services like Heart Rate (180D), Battery Service (180F), and Device Information (180A).",
            "snippet_highlighted_words": ["Heart Rate", "180D"],
        },
        {
            "position": 5,
            "title": "Heart Rate Monitor BLE Implementation Guide",
            "link": "https://github.com/example/ble-heart-rate",
            "displayed_link": "github.com › example",
            "snippet": "Implementation of BLE Heart Rate Service (UUID: 0000180d-0000-1000-8000-00805f9b34fb) for embedded devices.",
            "snippet_highlighted_words": ["Heart Rate Service"],
        },
    ],
}

# Nordic UART Service (vendor-specific) response
NORDIC_UART_SERVICE_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "def456",
        "status": "Success",
    },
    "search_parameters": {
        "engine": "google",
        "q": '"6e400001-b5a3-f393-e0a9-e50e24dcca9e" bluetooth OR BLE OR service OR GATT OR beacon',
    },
    "organic_results": [
        {
            "position": 1,
            "title": "Nordic UART Service (NUS) - Nordic Semiconductor",
            "link": "https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/bluetooth_services/nus.html",
            "displayed_link": "developer.nordicsemi.com › nRF_Connect_SDK",
            "snippet": "The Nordic UART Service (NUS) with UUID 6e400001-b5a3-f393-e0a9-e50e24dcca9e provides a serial port emulation over BLE.",
        },
        {
            "position": 2,
            "title": "BLE UART Service Tutorial",
            "link": "https://learn.adafruit.com/introduction-to-bluetooth-low-energy/uart-service",
            "displayed_link": "learn.adafruit.com › introduction",
            "snippet": "The Nordic UART Service (NUS) is commonly used for serial communication over Bluetooth Low Energy.",
        },
    ],
}

# Empty results (unknown UUID)
EMPTY_RESULTS_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "ghi789",
        "status": "Success",
    },
    "search_parameters": {
        "engine": "google",
        "q": '"12345678-1234-1234-1234-123456789abc" bluetooth OR BLE OR service OR GATT OR beacon',
    },
    "organic_results": [],
}

# Battery Service response
BATTERY_SERVICE_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "jkl012",
        "status": "Success",
    },
    "search_parameters": {
        "engine": "google",
        "q": '"0000180f-0000-1000-8000-00805f9b34fb" bluetooth OR BLE OR service OR GATT OR beacon',
    },
    "organic_results": [
        {
            "position": 1,
            "title": "Battery Service - Bluetooth SIG",
            "link": "https://www.bluetooth.com/specifications/gatt/services/",
            "displayed_link": "www.bluetooth.com",
            "snippet": "The Battery Service exposes the battery level of a device. UUID: 0x180F",
        },
        {
            "position": 2,
            "title": "BLE Battery Service Implementation",
            "link": "https://www.ti.com/tool/BLE-STACK",
            "displayed_link": "ti.com",
            "snippet": "Standard Bluetooth Low Energy Battery Service for monitoring device battery state.",
        },
    ],
}

# Response with ads (should be filtered out)
RESPONSE_WITH_ADS: dict[str, Any] = {
    "search_metadata": {
        "id": "mno345",
        "status": "Success",
    },
    "ads": [
        {
            "position": 1,
            "title": "Buy Bluetooth Devices - Shop Now",
            "link": "https://www.example-shop.com/bluetooth",
        }
    ],
    "organic_results": [
        {
            "position": 1,
            "title": "Heart Rate Service Documentation",
            "link": "https://www.bluetooth.com/specifications/",
            "displayed_link": "www.bluetooth.com",
            "snippet": "Heart Rate Service for BLE devices.",
        },
    ],
}

# Error response (API failure simulation)
ERROR_RESPONSE: dict[str, Any] = {
    "error": "Invalid API key. Your API key should be here: https://serpapi.com/manage-api-key",
}

# iBeacon UUID response
IBEACON_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "pqr678",
        "status": "Success",
    },
    "search_parameters": {
        "engine": "google",
        "q": '"E2C56DB5-DFFB-48D2-B060-D0F5A71096E0" bluetooth OR BLE OR beacon',
    },
    "organic_results": [
        {
            "position": 1,
            "title": "iBeacon Specification - Apple Developer",
            "link": "https://developer.apple.com/ibeacon/",
            "displayed_link": "developer.apple.com",
            "snippet": "iBeacon is a protocol developed by Apple. The standard proximity UUID E2C56DB5-DFFB-48D2-B060-D0F5A71096E0 is commonly used for testing.",
        },
        {
            "position": 2,
            "title": "Understanding iBeacon UUID",
            "link": "https://developer.estimote.com/ibeacon/",
            "displayed_link": "developer.estimote.com",
            "snippet": "An iBeacon advertisement contains a proximity UUID that identifies the beacon.",
        },
    ],
}

# Device Information Service response
DEVICE_INFO_SERVICE_RESPONSE: dict[str, Any] = {
    "search_metadata": {
        "id": "stu901",
        "status": "Success",
    },
    "search_parameters": {
        "engine": "google",
        "q": '"0000180a-0000-1000-8000-00805f9b34fb" bluetooth OR BLE OR service',
    },
    "organic_results": [
        {
            "position": 1,
            "title": "Device Information Service - Bluetooth SIG",
            "link": "https://www.bluetooth.com/specifications/gatt/services/",
            "displayed_link": "www.bluetooth.com",
            "snippet": "The Device Information Service (0x180A) exposes manufacturer and model information.",
        },
    ],
}


def get_mock_response(uuid: str) -> dict[str, Any]:
    """Get a mock SerpAPI response based on UUID.

    Args:
        uuid: The UUID to get a mock response for.

    Returns:
        Mock SerpAPI response dictionary.
    """
    uuid_lower = uuid.lower().replace("-", "")

    # Map UUIDs to responses
    responses = {
        "0000180d00001000800000805f9b34fb": HEART_RATE_SERVICE_RESPONSE,
        "6e400001b5a3f393e0a9e50e24dcca9e": NORDIC_UART_SERVICE_RESPONSE,
        "0000180f00001000800000805f9b34fb": BATTERY_SERVICE_RESPONSE,
        "0000180a00001000800000805f9b34fb": DEVICE_INFO_SERVICE_RESPONSE,
        "e2c56db5dffb48d2b060d0f5a71096e0": IBEACON_RESPONSE,
    }

    return responses.get(uuid_lower, EMPTY_RESULTS_RESPONSE)
