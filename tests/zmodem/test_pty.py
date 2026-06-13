import pty
import os
import sys

def test_pty():
    pid, fd = pty.fork()
    if pid == 0:
        # Child
        os.write(sys.stdout.fileno(), b'**\x18B00\n')
        sys.exit(0)
    else:
        # Parent
        data = os.read(fd, 1024)
        print(repr(data))
