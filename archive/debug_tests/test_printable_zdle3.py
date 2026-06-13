import pty
import os
import subprocess
import select
import threading

with open("test_payload.bin", "wb") as f:
    f.write(b"Hello World")

m_rz, s_rz = pty.openpty()
m_sz, s_sz = pty.openpty()

# Start receiver
rz = subprocess.Popen(["python3", "rzaio.py", "--zdle", "23", "--debug", "--directory", "."],
                      stdin=s_rz, stdout=subprocess.PIPE)

# Start sender
sz = subprocess.Popen(["python3", "szaio.py", "--zdle", "23", "--debug", "-e", "test_payload.bin"],
                      stdin=subprocess.PIPE, stdout=s_rz)

def forward(src, dst, name):
    while True:
        data = src.read(1)
        if not data:
            break
        print(f"{name}: {data!r}")
        dst.write(data)
        dst.flush()

t1 = threading.Thread(target=forward, args=(rz.stdout, sz.stdin, "RZ->SZ"))
t1.daemon = True
t1.start()

sz.wait()
rz.terminate()
