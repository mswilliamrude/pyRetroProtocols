import pty
import os
import subprocess
import select

with open("test_payload.bin", "wb") as f:
    f.write(bytes([i for i in range(256)]))

m_rz, s_rz = pty.openpty()
m_sz, s_sz = pty.openpty()

# Start receiver
rz = subprocess.Popen(["python3", "rzaio.py", "--zdle", "23", "--debug", "--directory", "."],
                      stdin=s_rz, stdout=s_sz)

# Start sender
sz = subprocess.Popen(["python3", "szaio.py", "--zdle", "23", "--debug", "-e", "test_payload.bin"],
                      stdin=s_sz, stdout=s_rz)

sz.wait()
rz.wait()

print("sz exit:", sz.returncode)
print("rz exit:", rz.returncode)
