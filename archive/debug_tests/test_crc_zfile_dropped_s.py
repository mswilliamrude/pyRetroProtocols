import sys
sys.path.append('.')
from modem.protocol.zmodem import ZMODEM
z = ZMODEM(None, None)

data4 = b'z.py\050328 0 0 0\0'
crc = 0
for b in data4:
    crc = z.calc_crc16(bytes([b]), crc)
crc = z.calc_crc16(bytes([0x6b]), crc)
print(f'data4 (dropped s): {crc:04x}')
