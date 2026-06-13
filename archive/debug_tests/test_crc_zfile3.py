import sys
sys.path.append('.')
from modem.protocol.zmodem import ZMODEM
z = ZMODEM(None, None)

# what if rz didn't decode #@ into \0 ?
data3 = b'sz.py#@50328 0 0 0#@'
crc = 0
for b in data3:
    crc = z.calc_crc16(bytes([b]), crc)
crc = z.calc_crc16(bytes([0x6b]), crc) # #k -> ZCRCW -> 0x6b
print(f'data3 (undecoded): {crc:04x}')

