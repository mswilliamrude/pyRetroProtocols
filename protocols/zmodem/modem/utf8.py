class QPStreamEncoder:
    def __init__(self, putc):
        self._putc = putc

    def putc(self, data: bytes, timeout=1):
        out = bytearray()
        for b in data:
            if b == 0x3d: # '='
                out.extend(b'=3D')
            elif 0x20 <= b <= 0x7e:
                out.append(b)
            elif b == 0x0d or b == 0x0a:
                out.append(b)
            else:
                out.extend(f"={b:02X}".encode('ascii'))
        if out:
            self._putc(bytes(out), timeout)

class QPStreamDecoder:
    def __init__(self, getc):
        self._getc = getc
        self.buf = bytearray()

    def getc(self, size, timeout=1):
        out = bytearray()
        while len(out) < size:
            if self.buf:
                out.append(self.buf.pop(0))
                continue
                
            chunk = self._getc(1, timeout)
            if not chunk:
                break
                
            b = chunk[0]
            if b == 0x3d: # '='
                hex_str = bytearray()
                c1 = self._getc(1, timeout)
                if not c1: break
                hex_str.extend(c1)
                
                c2 = self._getc(1, timeout)
                if not c2: break
                hex_str.extend(c2)
                
                try:
                    out.append(int(hex_str, 16))
                except ValueError:
                    out.extend(b'=')
                    out.extend(hex_str)
            else:
                out.append(b)
                
        return bytes(out)
