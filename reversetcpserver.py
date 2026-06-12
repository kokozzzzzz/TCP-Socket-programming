import socket
import sys
import struct
import threading
from datetime import datetime

# 日志锁，防止多线程写入混乱
log_lock = threading.Lock()
# 报文类型常量
TYPE_INIT    = 1
TYPE_AGREE   = 2
TYPE_REQUEST = 3
TYPE_ANSWER  = 4

#Initialization
def create_init_message(n: int) -> bytes:
    return struct.pack('!HI', TYPE_INIT, n)

#agree
def create_agree_message() -> bytes:
    return struct.pack('!H', TYPE_AGREE)

#reverseRequest
def create_request_message(data: bytes) -> bytes:
    length = len(data)
    return struct.pack('!HI', TYPE_REQUEST, length) + data

#reverseAnswer
def create_answer_message(data: bytes) -> bytes:
    length = len(data)
    return struct.pack('!HI', TYPE_ANSWER, length) + data

#socket
def recv_exactly(sock, n: int) -> bytes:
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed unexpectedly")
        data += chunk
    return data

#解析报文
def parse_message(sock):
    try:
        header = recv_exactly(sock, 2)
    except (ConnectionError, OSError):
        return None
    msg_type = struct.unpack('!H', header)[0]

    if msg_type == TYPE_AGREE:
        return (msg_type, None, None)

    #Length或者N
    len_bytes = recv_exactly(sock, 4)
    length = struct.unpack('!I', len_bytes)[0]

    if msg_type == TYPE_INIT:
        return (msg_type, length, None)

    data = recv_exactly(sock, length)
    return (msg_type, length, data)


def log_message(file, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    with log_lock:
        file.write(f"[{timestamp}] {msg}\n")
        file.flush()

#反转
def reverse_text(data: bytes) -> bytes:
    return data[::-1]


def handle_client(conn, addr, log_file):
    try:
        #Initialization
        msg = parse_message(conn)
        if not msg or msg[0] != TYPE_INIT:
            log_message(log_file, f"ERROR {addr} : Expected initialization, got {msg}")
            return
        n = msg[1]
        log_message(log_file, f"RECV initialization from {addr}, N={n}")

        #agree
        conn.sendall(create_agree_message())
        log_message(log_file, f"SEND agree to {addr}")

        #reverseRequest
        for i in range(n):
            msg = parse_message(conn)
            if not msg or msg[0] != TYPE_REQUEST:
                log_message(log_file, f"ERROR {addr} : Expected REQUEST, got {msg}")
                return
            _, length, data = msg
            log_message(log_file, f"RECV reverseRequest {i+1} from {addr}, length={length+6}")

            rev_data = reverse_text(data)
            conn.sendall(create_answer_message(rev_data))
            log_message(log_file, f"SEND reverseAnswer {i+1} to {addr}, length={len(rev_data)+6}")

    except Exception as e:
        log_message(log_file, f"EXCEPTION {addr}: {e}")
    finally:
        conn.close()
        log_message(log_file, f"CLOSED connection with {addr}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python reversetcpserver.py <端口号>")
        sys.exit(1)
    port = int(sys.argv[1])

    with open("run_log.txt", "a", encoding="utf-8") as log_file:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('0.0.0.0', port))
        server_sock.listen(10)
        print(f"Server listening on port {port} ...")

        try:
            while True:
                conn, addr = server_sock.accept()
                log_message(log_file, f"NEW connection from {addr}")
                t = threading.Thread(target=handle_client, args=(conn, addr, log_file))
                t.daemon = True
                t.start()
        except KeyboardInterrupt:
            print("\nServer shutting down.")
        finally:
            server_sock.close()

if __name__ == "__main__":
    main()