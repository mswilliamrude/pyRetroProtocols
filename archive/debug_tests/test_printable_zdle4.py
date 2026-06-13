import pty
import os
import subprocess

with open("test_payload.bin", "wb") as f:
    f.write(b"Hello World")

m_rz, s_rz = pty.openpty()
m_sz, s_sz = pty.openpty()

# Start receiver. Needs a directory instead of a positional output name!
rz = subprocess.Popen(["python3", "rzaio.py", "--zdle", "23", "--directory", "."],
                      stdin=s_rz, stdout=s_sz)

# Start sender
sz = subprocess.Popen(["python3", "szaio.py", "--zdle", "23", "-e", "test_payload.bin"],
                      stdin=s_sz, stdout=s_rz)

sz.wait()
rz.wait()

print("File size:", os.path.getsize("test_payload.bin"))
print("Return codes:", sz.returncode, rz.returncode)
