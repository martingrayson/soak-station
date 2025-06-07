import pytest
from custom_components.soakstation.mira.helpers.generic import (
    _crc,
    _get_payload_with_crc,
    _convert_temperature,
    _convert_temperature_reverse,
    _format_bytearray,
    _bits_to_list,
    _split_chunks
)

def test_crc():
    """Test CRC-16 calculation."""
    # Test with known values
    test_data = bytes([0x01, 0x02, 0x03, 0x04])
    crc = _crc(test_data)
    assert isinstance(crc, int)
    assert 0 <= crc <= 0xFFFF  # Should be 16-bit value

    # Test with empty data
    assert _crc(bytes()) == 0xFFFF  # Initial value

    # Test with single byte
    assert _crc(bytes([0x00])) != _crc(bytes([0x01]))  # Different inputs should give different CRCs

def test_get_payload_with_crc():
    """Test payload CRC generation."""
    payload = bytes([0x01, 0x02, 0x03])
    client_id = 0x1234
    
    result = _get_payload_with_crc(payload, client_id)
    
    assert len(result) == len(payload) + 2  # Original payload + 2 bytes CRC
    assert result[:len(payload)] == payload  # Original payload should be unchanged
    assert isinstance(result[-2:], bytes)  # Last 2 bytes should be CRC

def test_temperature_conversion():
    """Test temperature conversion in both directions."""
    test_temps = [0.0, 25.5, 38.0, 45.7, 99.9]
    
    for temp in test_temps:
        # Convert to device format and back
        device_format = _convert_temperature(temp)
        assert len(device_format) == 2  # Should be 2 bytes
        
        converted_back = _convert_temperature_reverse(device_format)
        assert abs(converted_back - temp) < 0.1  # Allow small floating point differences

    # Test edge cases
    assert _convert_temperature_reverse(_convert_temperature(-10.0)) == 0.0  # Should clamp to 0
    assert _convert_temperature_reverse(_convert_temperature(1000.0)) == 6553.5  # Should clamp to max

def test_format_bytearray():
    """Test bytearray formatting."""
    test_data = bytes([0x00, 0xFF, 0x0A, 0xB5])
    result = _format_bytearray(test_data)
    
    assert isinstance(result, str)
    assert result == "00,ff,0a,b5"  # Should be comma-separated hex values
    
    # Test with empty bytearray
    assert _format_bytearray(bytes()) == ""

def test_bits_to_list():
    """Test bit field to list conversion."""
    # Test with known values
    assert _bits_to_list(0b1010, 4) == [1, 3]  # Bits 1 and 3 are set
    assert _bits_to_list(0b1111, 4) == [0, 1, 2, 3]  # All bits set
    assert _bits_to_list(0b0000, 4) == []  # No bits set
    
    # Test with different lengths
    assert _bits_to_list(0xFF, 8) == list(range(8))  # All bits set in 8-bit field
    assert _bits_to_list(0xFF, 4) == list(range(4))  # Only first 4 bits considered

def test_split_chunks():
    """Test data chunking."""
    test_data = bytes([1, 2, 3, 4, 5, 6, 7, 8])
    
    # Test with different chunk sizes
    assert _split_chunks(test_data, 2) == [bytes([1, 2]), bytes([3, 4]), bytes([5, 6]), bytes([7, 8])]
    assert _split_chunks(test_data, 3) == [bytes([1, 2, 3]), bytes([4, 5, 6]), bytes([7, 8])]
    assert _split_chunks(test_data, 4) == [bytes([1, 2, 3, 4]), bytes([5, 6, 7, 8])]
    
    # Test with empty data
    assert _split_chunks(bytes(), 2) == []
    
    # Test with chunk size larger than data
    assert _split_chunks(test_data, 10) == [test_data]
    
    # Test with chunk size of 1
    assert _split_chunks(test_data, 1) == [bytes([x]) for x in test_data] 