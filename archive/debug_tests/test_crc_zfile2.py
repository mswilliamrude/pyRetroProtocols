import sys
sys.path.append('.')
from modem.protocol.zmodem import ZMODEM
z = ZMODEM(None, None)

data = b'sz.py\050328 0 0 0\0'
crc = 0
for b in data:
    crc = z.calc_crc16(bytes([b]), crc)
crc = z.calc_crc16(bytes([0x6b]), crc)
print(f'data1: {crc:04x}')

data2 = b'sz.py\050328 0 0 0'
crc = 0
for b in data2:
    crc = z.calc_crc16(bytes([b]), crc)
crc = z.calc_crc16(bytes([0x6b]), crc)
print(f'data2: {crc:04x}')
