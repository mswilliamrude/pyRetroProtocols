def crc16(data, crc=0):
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
    return crc & 0xFFFF

def crc24(data, crc=0):
    # Common 24-bit polynomial 0x864CFB
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            if crc & 0x800000:
                crc = (crc << 1) ^ 0x864CFB
            else:
                crc <<= 1
    return crc & 0xFFFFFF

def crc32(data, crc=0):
    # Common 32-bit polynomial 0x04C11DB7 (ISO HDLC)
    crc ^= 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF

import time

def unix_to_dos_time(timestamp: float) -> int:
    """
    Converts a Unix timestamp to a 32-bit DOS packed ftime.
    High 16 bits: Date (YYYYYYYM MMMDDDDD)
    Low 16 bits: Time (HHHHHMMM MMMSSSSS)
    """
    t = time.localtime(timestamp)
    year = max(0, t.tm_year - 1980)
    dos_date = (year << 9) | (t.tm_mon << 5) | t.tm_mday
    dos_time = (t.tm_hour << 11) | (t.tm_min << 5) | (t.tm_sec // 2)
    return (dos_date << 16) | dos_time
