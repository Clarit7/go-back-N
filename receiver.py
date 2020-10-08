# receiver.py - The receiver in the reliable data transer protocol
import packet
import socket
import sys
import udt
import time
import _thread

RECEIVER_ADDR = ('localhost', 8080)
UNIT_TIME = 0.001           # 단위 시간
RTT = 100 * UNIT_TIME       # RTT = 100 단위시간

mutex = _thread.allocate_lock()
rtt_q = []            # RTT 구현을 위한 queue
rtt_timer = []        # RTT 구현시 시간정보를 저장하는 queue

# 패킷 receive
def receive(sock):
    global mutex

    expected_num = 0
    while True:
        mutex.acquire()
        pkt, addr = udt.recv(sock)
        if not pkt:
            break
        seq_num, data = packet.extract(pkt)  # packet 수신
        print('Got packet', seq_num)

        if seq_num == expected_num:  # 오류 없이 수신되는 경우
            print('Expected packet. Sending ACK', expected_num)
            pkt = packet.make(expected_num)
            udt.send(pkt, sock, addr)
            rtt_q.append([pkt, sock, addr])
            rtt_timer.append(time.time())
            expected_num += 1
        else:                        # 오류로 인해 순서가 잘못 수신되는 경우
            print('Unexpected packet. Sending ACK', expected_num - 1)
            pkt = packet.make(expected_num - 1)
            udt.send(pkt, sock, addr)
            rtt_q.append([pkt, sock, addr])
            rtt_timer.append(time.time())

        time.sleep(UNIT_TIME)
        mutex.release()

# ACK를 지정된 rtt의 절반의 시간만큼 Queue에서 대기시킨 후에 송신
def rtt_queue():
    global mutex
    global rtt_q
    global rtt_timer

    while(True):
        mutex.acquire(0)
        if len(rtt_q) > 0 and time.time() - rtt_timer[0] >= RTT/2:
            rtt_timer.pop(0)
            pac, soc, addr = rtt_q.pop()
            udt.send(pac, soc, addr)
        mutex.release()

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(RECEIVER_ADDR)
    receive(sock)
    sock.close()
