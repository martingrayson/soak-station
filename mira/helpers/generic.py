import struct

def _crc(data):
    i = 0
    i2 = 0xFFFF
    while i < len(data):
        b = data[i]
        i3 = i2
        for i2 in range(8):
            i4 = 1
            i5 = 1 if ((b >> (7 - i2)) & 1) == 1 else 0
            if ((i3 >> 15) & 1) != 1:
                i4 = 0
            i3 = i3 << 1
            if (i5 ^ i4) != 0:
                i3 = i3 ^ 0x1021
        i += 1
        i2 = i3
    return i2 & 0xFFFF

def _get_payload_with_crc(payload, client_id):
    crc = _crc(payload + struct.pack(">I", client_id))
    return payload + struct.pack(">H", crc)


def _convert_temperature(celsius):
    value = int(max(0, min((1 << 16) - 1, round(celsius * 10))))
    return struct.pack(">H", value)


def _convert_temperature_reverse(mira_temp):
    return struct.unpack(">H", mira_temp)[0] / 10.0


def _format_bytearray(ba):
    return ",".join(format(b, "02x") for b in ba)


def _bits_to_list(bits, length):
    bits_list = []
    for i in range(0, length):
        if bits >> i & 1:
            bits_list.append(i)
    return bits_list


def _split_chunks(data, chunk_size):
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
