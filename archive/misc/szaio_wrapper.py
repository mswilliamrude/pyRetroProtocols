
import sys
import subprocess
with open("/tmp/szaio_read.log", "wb") as log_f:
    p = subprocess.Popen(["python3", "szaio.py", "--zdle", "23", "--debug", "-e", "test_payload.bin"], stdin=sys.stdin, stdout=sys.stdout)
    p.wait()
