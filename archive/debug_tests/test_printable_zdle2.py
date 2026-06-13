import subprocess
p = subprocess.Popen("""
python3 rzaio.py --zdle 23 --debug --directory . < pipe1 > pipe2 &
python3 szaio.py --zdle 23 --debug -e test_payload.bin < pipe2 > pipe1
""", shell=True)
p.wait()
