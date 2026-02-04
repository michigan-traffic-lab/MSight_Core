import socket
import time

host, port = "localhost", 46092
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
while True:
    sock.sendto(b"hello", (host, port))
    print(f"send to {host}:{port}")
    # data = sock.recv(1024)
    time.sleep(1)

