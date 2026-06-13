import sys
sys.path.insert(0, ".")
from modem.protocol.zmodem import ZMODEM

sz = ZMODEM(None, None)
rz = ZMODEM(None, None)

buf = []
def putc(data, timeout=1):
    buf.extend(list(data))
sz.putc = putc

sz._send_hex_header([1, 0, 0, 0, 103], 1)

idx = 0
def getc(size, timeout=1):
    global idx
    if idx >= len(buf): return None
    res = bytes(buf[idx:idx+size])
    idx += size
    return res

rz.getc = getc
# read up to ZPAD, ZPAD, ZDLE, ZHEX
for _ in range(4):
    rz.getc(1)

res = rz._recv_hex_header(1)
print(res)

