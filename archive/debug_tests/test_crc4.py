import sys
sys.path.insert(0, ".")
from modem.protocol.zmodem import ZMODEM
zm = ZMODEM(None, None)

data = b'0100000067a69a\r\n\x11'
idx = 0
def getc(size, timeout=1):
    global idx
    if idx >= len(data):
        return None
    res = data[idx:idx+size]
    idx += size
    return res
zm.getc = getc
res = zm._recv_hex_header(1)
print(res)
