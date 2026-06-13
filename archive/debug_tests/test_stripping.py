import sys
import time

print("\r\nTesting which bytes survive the PTY/Bastion connection...\r\n")

# We will send all bytes from 0x01 to 0x1F
# We will format them safely
for i in range(1, 32):
    sys.stdout.buffer.write(b"BYTE_TEST: ")
    sys.stdout.buffer.write(bytes([i]))
    sys.stdout.buffer.write(b" :END_TEST\r\n")
    sys.stdout.buffer.flush()
    time.sleep(0.1)

print("\r\nDone testing.\r\n")
