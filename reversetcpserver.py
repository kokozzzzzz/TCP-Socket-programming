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

def create_init_message(n: int) -> bytes:
    """创建 Initialization 报文: Type=1 (2B) + N (4B)"""
    return struct.pack('!HI', TYPE_INIT, n)

def create_agree_message() -> bytes:
    """创建 agree 报文: Type=2 (2B)"""
    return struct.pack('!H', TYPE_AGREE)

def create_request_message(data: bytes) -> bytes:
    """创建 reverseRequest 报文: Type=3 (2B) + Length (4B) + Data"""
    length = len(data)
    return struct.pack('!HI', TYPE_REQUEST, length) + data

def create_answer_message(data: bytes) -> bytes:
    """创建 reverseAnswer 报文: Type=4 (2B) + Length (4B) + Data"""
    length = len(data)
    return struct.pack('!HI', TYPE_ANSWER, length) + data

def recv_exactly(sock, n: int) -> bytes:
    """从 socket 精确接收 n 字节数据"""
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed unexpectedly")
        data += chunk
    return data

def parse_message(sock):
    """
    从 socket 接收并解析一个报文。
    返回值:
        - 对于 agree: (type, None, None)
        - 对于 init : (type, N, None)
        - 对于 request/answer: (type, length, data)
        - 连接关闭或错误: None
    """
    try:
        # 读取 Type (2字节)
        header = recv_exactly(sock, 2)
    except (ConnectionError, OSError):
        return None
    msg_type = struct.unpack('!H', header)[0]

    if msg_type == TYPE_AGREE:
        return (msg_type, None, None)

    # 其他类型均有 4 字节 Length / N
    len_bytes = recv_exactly(sock, 4)
    length = struct.unpack('!I', len_bytes)[0]

    if msg_type == TYPE_INIT:
        # 对于 INIT，length 就是 N，没有后续数据
        return (msg_type, length, None)

    # REQUEST 或 ANSWER，继续读取 Data
    data = recv_exactly(sock, length)
    return (msg_type, length, data)


def log_message(file, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    with log_lock:
        file.write(f"[{timestamp}] {msg}\n")
        file.flush()

def reverse_text(data: bytes) -> bytes:
    """将字节串整体反转"""
    return data[::-1]

def handle_client(conn, addr, log_file):
    """处理单个客户端的所有请求"""
    try:
        # 1. 接收 Initialization
        msg = parse_message(conn)
        if not msg or msg[0] != TYPE_INIT:
            log_message(log_file, f"ERROR {addr} : Expected initialization, got {msg}")
            return
        n = msg[1]  #块数
        log_message(log_file, f"RECV initialization from {addr}, N={n}")

        # 2. 发送 agree
        conn.sendall(create_agree_message())
        log_message(log_file, f"SEND agree to {addr}")

        # 3. 循环处理 n 个 reverseRequest
        for i in range(n):
            msg = parse_message(conn)
            if not msg or msg[0] != TYPE_REQUEST:
                log_message(log_file, f"ERROR {addr} : Expected REQUEST, got {msg}")
                return
            _, length, data = msg
            log_message(log_file, f"RECV reverseRequest {i+1} from {addr}, length={length}")

            rev_data = reverse_text(data)
            conn.sendall(create_answer_message(rev_data))
            log_message(log_file, f"SEND reverseAnswer {i+1} to {addr}, length={len(rev_data)}")

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