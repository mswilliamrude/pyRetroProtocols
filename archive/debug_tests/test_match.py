import re

snoop_buffer = b'\r\n[PyZMODEM] Tip: Press Ctrl+X 5 times to abort the transfer at any time.\r\n\r\n**\x18B00000000000000\r\n\x11'

idx = -1
if b'**\x18B00' in snoop_buffer:
    print("Found it!")
else:
    print("Not found")

idx = snoop_buffer.find(b'**\x18B00')
print(f"Index: {idx}")
