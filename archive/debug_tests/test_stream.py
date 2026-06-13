class QPStreamEncoder:
    def encode(self, data: bytes) -> bytes:
        out = bytearray()
        for b in data:
            if b == 0x3d: # '='
                out.extend(b'=3D')
            elif 0x20 <= b <= 0x7e:
                out.append(b)
            else:
                out.extend(f"={b:02X}".encode('ascii'))
        return bytes(out)

class QPStreamDecoder:
    def __init__(self):
        self.buf = bytearray()
    def decode(self, data: bytes) -> bytes:
        self.buf.extend(data)
        out = bytearray()
        i = 0
        while i < len(self.buf):
            if self.buf[i] == 0x3d: # '='
                if i + 2 < len(self.buf):
                    hex_str = self.buf[i+1:i+3]
                    try:
                        out.append(int(hex_str, 16))
                    except ValueError:
                        pass # Corrupt stream
                    i += 3
                else:
                    break # Wait for more bytes
            else:
                out.append(self.buf[i])
                i += 1
        self.buf = self.buf[i:]
        return bytes(out)

enc = QPStreamEncoder()
dec = QPStreamDecoder()
encoded = enc.encode(b"**#B00\r\n\x11sz.py\0\xd0")
print("Encoded:", encoded)
decoded = dec.decode(encoded)
print("Decoded:", decoded)
