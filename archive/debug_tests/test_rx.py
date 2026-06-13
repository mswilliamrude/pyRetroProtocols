import re
log = """
RZ: 2026-06-02 15:38:32,192 [DEBUG] PTY READ: b'\n[PyZMODEM] Tip: Press Ctrl+X 5 times to abort the transfer at any time.\r\n\n**B00000000000000\r\n'
"""
print(b'**\x18B00' in b'\n[PyZMODEM] Tip: Press Ctrl+X 5 times to abort the transfer at any time.\r\n\n**B00000000000000\r\n')
