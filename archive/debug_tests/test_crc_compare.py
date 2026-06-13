import sys
sys.path.insert(0, ".")
from modem.tools import crc16, CRC16_MAP

def lrzsz_updcrc(cp, crc):
    return (CRC16_MAP[((crc >> 8) & 255)] ^ ((crc << 8) & 0xffff) ^ cp) & 0xffff

def pyzmodem_crc16(byte, crc=0):
    b = byte if isinstance(byte, int) else ord(byte)
    crc = ((crc << 8) & 0xffff) ^ CRC16_MAP[((crc >> 0x08) ^ b) & 0xff]
    return crc

c1, c2 = 0, 0
for b in [1, 0, 0, 0, 103]:
    c1 = lrzsz_updcrc(b, c1)
    c2 = pyzmodem_crc16(b, c2)

print(hex(c1), hex(c2))

# What about lrzsz_updcrc with zeros?
c1_zero = lrzsz_updcrc(0, lrzsz_updcrc(0, c1))
c2_zero = pyzmodem_crc16(0, pyzmodem_crc16(0, c2))
print("With zeros:", hex(c1_zero), hex(c2_zero))

