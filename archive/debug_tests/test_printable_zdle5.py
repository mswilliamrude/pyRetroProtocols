import pty
import os
import subprocess
import threading

with open("test_payload.bin", "wb") as f:
    f.write(b"Hello World")

m_rz, s_rz = pty.openpty()
m_sz, s_sz = pty.openpty()

rz = subprocess.Popen(["python3", "rzaio.py", "--zdle", "23", "--debug", "--directory", "."],
                      stdin=s_rz, stdout=s_rz)

sz = subprocess.Popen(["python3", "szaio.py", "--zdle", "23", "--debug", "-e", "test_payload.bin"],
                      stdin=s_sz, stdout=s_sz)

def forward(fd_in, fd_out):
    while True:
        try:
            data = os.read(fd_in, 1024)
            if not data: break
            os.write(fd_out, data)
        except OSError:
            break

t1 = threading.Thread(target=forward, args=(m_rz, m_sz))
t2 = threading.Thread(target=forward, args=(m_sz, m_rz))
t1.daemon = True
t2.daemon = True
t1.start()
t2.start()

sz.wait()
rz.terminate()
print("Success!")
