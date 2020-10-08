# udt.py - Unreliable data transfer using UDP
import random
import socket
import time

DROP_PROB = 9

# 10% 확률로 PACKET 전송에 실패함
def send(packet, sock, addr):
    if random.randint(0, DROP_PROB) > 0:
        sock.sendto(packet, addr)
    else:
        print("********************** PACKET LOST!!!!")
    return

# Receive a packet from the unreliable channel
def recv(sock):
    packet, addr = sock.recvfrom(1024)
    return packet, addr
