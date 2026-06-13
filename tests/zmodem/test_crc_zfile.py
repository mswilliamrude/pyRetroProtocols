import binascii

def crc16(data):
    crc = 0
    for b in data:
        crc = crc ^ (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc

# Wait, zmodem crc is different. Let's use the one in pyzmodem
