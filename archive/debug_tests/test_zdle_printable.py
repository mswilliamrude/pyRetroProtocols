import subprocess
import os
import pty
import time

# Create dummy file to send
with open("/tmp/dummy_file2.txt", "w") as f:
    f.write("Hello ZMODEM printable world!\n")

r_rz, w_sz = os.pipe()
r_sz, w_rz = os.pipe()

rz_proc = subprocess.Popen(
    ["python3", "rzaio.py", "--debug", "--zdle", "23", "-e"],
    stdin=r_rz, stdout=w_rz, stderr=subprocess.PIPE,
    cwd=os.getcwd()
)

sz_proc = subprocess.Popen(
    ["python3", "szaio.py", "--debug", "--zdle", "23", "-e", "/tmp/dummy_file2.txt"],
    stdin=r_sz, stdout=w_sz, stderr=subprocess.PIPE,
    cwd=os.getcwd()
)

sz_out, sz_err = sz_proc.communicate()
rz_out, rz_err = rz_proc.communicate()

print("SZ ERR:", sz_err.decode())
print("RZ ERR:", rz_err.decode())
