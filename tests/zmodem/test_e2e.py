import subprocess
import os
import pty
import time

master_rz, slave_sz = pty.openpty()
master_sz, slave_rz = pty.openpty()

# Create dummy file to send
with open("/tmp/dummy_file.txt", "w") as f:
    f.write("Hello ZMODEM world!\n")

# rz reads from master_sz (sz's stdout), writes to master_rz (sz's stdin)
# Wait, this PTY cross-connect is tricky.
# It's better to use os.pipe()

r_rz, w_sz = os.pipe()
r_sz, w_rz = os.pipe()

rz_proc = subprocess.Popen(
    ["python3", "rzaio.py", "--debug", "--zdle", "29", "-e"],
    stdin=r_rz, stdout=w_rz, stderr=subprocess.PIPE,
    cwd=os.getcwd()
)

sz_proc = subprocess.Popen(
    ["python3", "szaio.py", "--debug", "--zdle", "29", "-e", "/tmp/dummy_file.txt"],
    stdin=r_sz, stdout=w_sz, stderr=subprocess.PIPE,
    cwd=os.getcwd()
)

sz_out, sz_err = sz_proc.communicate()
rz_out, rz_err = rz_proc.communicate()

print("SZ ERR:", sz_err.decode())
print("RZ ERR:", rz_err.decode())
