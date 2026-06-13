import os
import threading
import sys
import time
from szaio import main as sz_main
from rzaio import main as rz_main

sys.argv = ['szaio', '--utf8', 'dummy_file.txt']

def run_sz():
    try:
        sz_main()
    except Exception as e:
        print("sz crashed", e)

def run_rz():
    sys.argv = ['rzaio', '--utf8']
    try:
        rz_main()
    except Exception as e:
        print("rz crashed", e)

if __name__ == '__main__':
    with open('dummy_file.txt', 'wb') as f:
        f.write(b'\xd0' * 100) # lots of high bit characters
        
    r, w = os.pipe()
    r2, w2 = os.pipe()
    
    # We will simulate Bastion by dropping \xd0 in the pipe!
    def bastion_pipe(r_fd, w_fd):
        while True:
            try:
                data = os.read(r_fd, 1024)
            except:
                break
            if not data: break
            # if we drop \xd0 we simulate bastion
            data = data.replace(b'\xd0', b'')
            os.write(w_fd, data)

    # Let's not run bastion pipe just yet, just test standard pipe
    # sz stdout -> w -> r -> rz stdin
    # rz stdout -> w2 -> r2 -> sz stdin
    
    pid = os.fork()
    if pid == 0:
        # child is rz
        os.dup2(r, 0)
        os.dup2(w2, 1)
        os.close(r)
        os.close(w)
        os.close(r2)
        os.close(w2)
        run_rz()
        os._exit(0)
    else:
        # parent is sz
        os.dup2(r2, 0)
        os.dup2(w, 1)
        os.close(r)
        os.close(w)
        os.close(r2)
        os.close(w2)
        run_sz()
        os.waitpid(pid, 0)
