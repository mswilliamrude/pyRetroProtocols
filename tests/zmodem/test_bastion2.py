import os
import sys
import pytest


def proxy_loop(r_fd, w_fd):
    while True:
        try:
            data = os.read(r_fd, 4096)
        except:
            break
        if not data: break
        # Simulate Bastion dropping high-bit characters
        filtered = bytearray()
        for b in data:
            if b <= 0x7e: # Only pass ASCII!
                filtered.append(b)
            elif b == 0x0d or b == 0x0a:
                filtered.append(b)
            elif b == 0x11 or b == 0x13:
                pass # strip XON/XOFF too!
        if filtered:
            os.write(w_fd, bytes(filtered))


@pytest.mark.parametrize('dummy_file', ['dummy_file.txt'])
def test_bastion2(dummy_file):
    r_sz, w_sz = os.pipe() # rz writes to w_sz, proxy reads r_sz, proxy writes to sz
    r_rz, w_rz = os.pipe() # sz writes to w_rz, proxy reads r_rz, proxy writes to rz

    proxy_sz_r, proxy_sz_w = os.pipe()
    proxy_rz_r, proxy_rz_w = os.pipe()

    if os.fork() == 0:
        # Proxy sz -> rz
        os.close(proxy_rz_r)
        os.close(w_rz)
        proxy_loop(r_rz, proxy_rz_w)
        os._exit(0)

    if os.fork() == 0:
        # Proxy rz -> sz
        os.close(proxy_sz_r)
        os.close(w_sz)
        proxy_loop(r_sz, proxy_sz_w)
        os._exit(0)

    if os.fork() == 0:
        # RZ
        os.dup2(proxy_rz_r, 0)
        os.dup2(w_sz, 1)
        os.close(r_rz)
        os.close(proxy_sz_w)
        os.close(proxy_sz_r)
        os.close(r_sz)
        os.close(proxy_rz_w)
        
        from rzaio import main
        sys.argv = ['rzaio', '--utf8', '--zdle', '23']
        main()
        os._exit(0)

    # SZ
    os.dup2(proxy_sz_r, 0)
    os.dup2(w_rz, 1)
    os.close(r_sz)
    os.close(proxy_rz_w)
    os.close(proxy_rz_r)
    os.close(r_rz)
    os.close(proxy_sz_w)

    from szaio import main
    sys.argv = ['szaio', '--utf8', '--zdle', '23', dummy_file]
    main()
