import struct
from typing import List, Union

def _crc(data: bytes) -> int:
    """Calculate CRC-16 checksum for data.
    
    Uses CRC-16-CCITT-FALSE algorithm with polynomial 0x1021.
    
    Args:
        data: Bytes to calculate CRC for
        
    Returns:
        16-bit CRC value
    """
    i = 0
    i2 = 0xFFFF  # Initial value
    while i < len(data):
        b = data[i]
        i3 = i2
        # Process each bit of the byte
        for i2 in range(8):
            i4 = 1
            i5 = 1 if ((b >> (7 - i2)) & 1) == 1 else 0
            if ((i3 >> 15) & 1) != 1:
                i4 = 0
            i3 = i3 << 1
            if (i5 ^ i4) != 0:
                i3 = i3 ^ 0x1021  # CRC polynomial
        i += 1
        i2 = i3
    return i2 & 0xFFFF

def _get_payload_with_crc(payload: bytes, client_id: int) -> bytes:
    """Append CRC to payload using client ID.
    
    Args:
        payload: Data to append CRC to
        client_id: Client ID to include in CRC calculation
        
    Returns:
        Payload with 16-bit CRC appended
    """
    crc = _crc(payload + struct.pack(">I", client_id))
    return payload + struct.pack(">H", crc)

def _convert_temperature(celsius: float) -> bytes:
    """Convert Celsius temperature to device format.
    
    Args:
        celsius: Temperature in Celsius
        
    Returns:
        2-byte temperature value scaled by 10
    """
    value = int(max(0, min((1 << 16) - 1, round(celsius * 10))))
    return struct.pack(">H", value)

def _convert_temperature_reverse(mira_temp: bytes) -> float:
    """Convert device temperature format to Celsius.
    
    Args:
        mira_temp: 2-byte temperature value from device
        
    Returns:
        Temperature in Celsius
    """
    return struct.unpack(">H", mira_temp)[0] / 10.0

def _format_bytearray(ba: Union[bytes, bytearray]) -> str:
    """Format bytearray as hex string.
    
    Args:
        ba: Bytearray to format
        
    Returns:
        Comma-separated hex string
    """
    return ",".join(format(b, "02x") for b in ba)

def _bits_to_list(bits: int, length: int) -> List[int]:
    """Convert bit field to list of set bit positions.
    
    Args:
        bits: Integer bit field
        length: Number of bits to check
        
    Returns:
        List of positions where bits are set to 1
    """
    bits_list = []
    for i in range(0, length):
        if bits >> i & 1:
            bits_list.append(i)
    return bits_list

def _split_chunks(data: Union[bytes, bytearray], chunk_size: int) -> List[Union[bytes, bytearray]]:
    """Split data into chunks of specified size.
    
    Args:
        data: Data to split
        chunk_size: Size of each chunk
        
    Returns:
        List of data chunks
    """
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
