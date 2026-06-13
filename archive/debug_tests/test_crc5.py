import sys
sys.path.insert(0, ".")
from modem.protocol.zmodem import ZMODEM
zm = ZMODEM(None, None)

buf = []
def putc(data, timeout=1):
    buf.append(data)
zm.putc = putc

header = [1, 0, 0, 0, 103]
mine = 0
for char in header:
    mine = zm.calc_crc16(chr(char), mine)

print("Original mine before zeros:", hex(mine))
print("Zeros added:")
mine2 = zm.calc_crc16(chr(0), mine)
mine2 = zm.calc_crc16(chr(0), mine2)
print("Mine after zeros:", hex(mine2))

# What does updcrc in standard zmodem do?
