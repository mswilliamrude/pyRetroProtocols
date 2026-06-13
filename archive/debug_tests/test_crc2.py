import sys
sys.path.insert(0, ".")
from modem.protocol.zmodem import ZMODEM
zm = ZMODEM(None, None)

mine = 0
for char in [1, 0, 0, 0, 103]:
    mine = zm.calc_crc16(chr(char), mine)
print("Receiver mine:", hex(mine))

mine2 = 0
for char in [1, 0, 0, 0, 103]:
    mine2 = zm.calc_crc16(chr(char), mine2)
mine2_with_zeros = zm.calc_crc16(chr(0), mine2)
mine2_with_zeros = zm.calc_crc16(chr(0), mine2_with_zeros)
print("Sender CRC:", hex(mine2_with_zeros))

def crc16(data):
    crc = 0
    for byte in data:
        crc = zm.calc_crc16(chr(byte), crc)
    return zm.calc_crc16(chr(0), zm.calc_crc16(chr(0), crc))
print("Sender CRC (func):", hex(crc16([1, 0, 0, 0, 103])))
