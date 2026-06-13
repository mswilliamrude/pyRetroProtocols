import sys
sys.path.insert(0, ".")
from modem.protocol.zmodem import ZMODEM
zm = ZMODEM(None, None)
mine = 0
for char in [1, 0, 0, 0, 103]:
    mine = zm.calc_crc16(chr(char), mine)

print("Receiver calculated mine:", hex(mine))

mine2 = zm.calc_crc16(chr(0), mine)
mine2 = zm.calc_crc16(chr(0), mine2)
print("Sender calculated CRC:", hex(mine2))
