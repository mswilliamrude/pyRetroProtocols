import re
data = b'\r\n[PyZMODEM] Tip: Press Ctrl+X 5 times to abort the transfer at any time.\r\n**\x18B00000000000000\r\n\x11'
print(b'**\x18B00' in data)
