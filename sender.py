# sender.py - The sender in the reliable data transfer protocol
import packet
import socket
import sys
import _thread
import time
import udt

from timer import Timer

PACKET_SIZE = 10
RECEIVER_ADDR = ('localhost', 8080)
SENDER_ADDR = ('localhost', 0)
UNIT_TIME = 0.001                       # 단위 시간
RTT = 100 * UNIT_TIME                   # RTT = 100 단위시간
TIMEOUT = 150 * UNIT_TIME               # Timeout = 150 단위시간
WINDOW_SIZE = 10

process_start_time = 0
base = 0
mutex = _thread.allocate_lock()
send_timer = Timer(TIMEOUT)
rtt_q = []            # RTT 구현을 위한 queue
rtt_timer = []        # RTT 구현시 시간정보를 저장하는 queue

# 패킷의 가장 마지막 부분 출력시 윈도우 사이즈가 패킷을 넘어가지 않도록 조정
def set_window_size(num_packets):
    global base
    return min(WINDOW_SIZE, num_packets - base)

# packet 송신
def send(sock):
    global mutex
    global base
    global send_timer
    global rtt_q
    global rtt_timer
    global process_start_time

    packets = []
    packets_start_time = []

    for i in range(1000):
        data = "packet" + str(i)
        packets.append(packet.make(i, data.encode()))
        packets_start_time.append(None)

    num_packets = len(packets)

    # 파라미터 정보 출력
    print('Number of packets :', num_packets)
    print('Unit time :', UNIT_TIME, 'seconds')
    print('RTT time :', RTT, 'seconds')
    print('Timeout :', TIMEOUT, 'seconds')
    print('Window size :', WINDOW_SIZE)

    window_size = set_window_size(num_packets)
    next_to_send = 0
    base = 0

    _thread.start_new_thread(receive, (sock, num_packets))
    _thread.start_new_thread(rtt_queue, ())

    process_start_time = time.time()

    while base < num_packets:
        mutex.acquire()

        while next_to_send < base + window_size:
            rtt_q.append([packets[next_to_send], sock, RECEIVER_ADDR])
            current_time = time.time()
            print('Sending packet', next_to_send, 'Time', round(time.time() - process_start_time, 3), 'seconds')
            print('Window state:', min(base, num_packets - 1), 'to', min(WINDOW_SIZE, num_packets - base) + base - 1)
            rtt_timer.append(current_time)
            time.sleep(UNIT_TIME)
            next_to_send += 1

        if not send_timer.running():
            send_timer.start()

        while send_timer.running() and not send_timer.timeout():
            mutex.release()
            mutex.acquire()

        # 송신한 packet의 timeout을 검사함
        if send_timer.timeout():
            print('Timeout')
            send_timer.stop();
            next_to_send = base
        else:
            window_size = set_window_size(num_packets)
        mutex.release()

    udt.send(packet.make_empty(), sock, RECEIVER_ADDR)

# packet을 지정된 rtt의 절반의 시간만큼 Queue에서 대기시킨 후에 송신
def rtt_queue():
    global mutex
    global rtt_q
    global rtt_timer

    while(True):
        mutex.acquire()
        if len(rtt_q) > 0 and time.time() - rtt_timer[0] >= RTT/2:
            rtt_timer.pop(0)
            pac, soc, addr = rtt_q.pop(0)
            udt.send(pac, soc, addr)

        mutex.release()

# ACK 수신
def receive(sock, num_packets):
    global mutex
    global base
    global send_timer
    global process_start_time

    print('Window state:', base, 'to', min(WINDOW_SIZE, num_packets - base) + base - 1)
    while True:
        pkt, _ = udt.recv(sock);
        ack, _ = packet.extract(pkt);

        mutex.acquire()
        print('Got ACK', ack, 'Time', round(time.time() - process_start_time, 3), 'seconds')
        if (ack >= base):
            base = ack + 1
            print('Window state:', min(base, num_packets - 1), 'to', min(WINDOW_SIZE, num_packets - base) + base - 1)
            send_timer.stop()

        mutex.release()

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SENDER_ADDR)
    send(sock)
    sock.close()
