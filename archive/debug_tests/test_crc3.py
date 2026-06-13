import sys
sys.path.insert(0, ".")
from modem.protocol.zmodem import ZMODEM
zm = ZMODEM(None, None)

buf = []
def putc(data, timeout=1):
    buf.append(data)
zm.putc = putc

zm._send_hex_header([1, 0, 0, 0, 103], 1)
print(buf[0])
