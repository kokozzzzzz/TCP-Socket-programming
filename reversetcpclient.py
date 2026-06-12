import socket
import struct
import sys
import random
import time
from datetime import datetime

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

def generate_chunk_sizes(file_len, lmin, lmax, seed):
    """
    根据种子随机生成每块长度。
    返回值：列表，包含每一块的字节数。
    """
    random.seed(seed)
    chunks = []
    remaining = file_len
    while remaining > 0:
        if remaining > lmax:
            chunk = random.randint(lmin, lmax)
        else:
            chunk = remaining      # 最后一块可能小于 lmin
        chunks.append(chunk)
        remaining -= chunk
    return chunks

def log_message(file, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    file.write(f"[{timestamp}] {msg}\n")
    file.flush()

def main():
    if len(sys.argv) != 8:
        print("Usage: python reversetcpclient.py <ip地址> <端口号> <最小值> <最大值> <种子>")
        sys.exit(1)

    server_ip   = sys.argv[1]
    port        = int(sys.argv[2])
    lmin        = int(sys.argv[3])
    lmax        = int(sys.argv[4])
    seed        = int(sys.argv[5])
    input_file = sys.argv[6]
    output_file = sys.argv[7]
    # input_file  = f"input.txt"
    # output_file = f"output.txt"

    # 读取整个文件
    with open(input_file, 'rb') as f:
        file_data = f.read()
    file_len = len(file_data)

    # 分块
    chunks = generate_chunk_sizes(file_len, lmin, lmax, seed)
    n = len(chunks)
    print(f"文件为{file_len}bytes,被分成{n}块")
    for i, size in enumerate(chunks):
        print(f"第{i+1}块大小为: {size} bytes")

    # 连接服务器
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, port))

    with open("run_log.txt", "a", encoding="utf-8") as log:
        # 1. 发送 Initialization
        sock.sendall(create_init_message(n))
        #log_message(log, f"SEND INIT to {server_ip}:{port}, N={n}")

        # 2. 等待 agree
        msg = parse_message(sock)
        if not msg or msg[0] != TYPE_AGREE:
            print("没有收到server的agree")
            return
        #log_message(log, f"RECV AGREE from {server_ip}:{port}")

        reversed_chunks = []    # 按接收顺序存储反转后的块
        offset = 0

        for i, chunk_size in enumerate(chunks):
            data = file_data[offset:offset+chunk_size]
            offset += chunk_size

            # 发送 reverseRequest
            sock.sendall(create_request_message(data))
            #log_message(log, f"SEND REQUEST {i+1}, length={chunk_size}")
            #人为延迟
            time.sleep(0.5)

            # 接收 reverseAnswer
            msg = parse_message(sock)
            if not msg or msg[0] != TYPE_ANSWER:
                print(f"没有收到第{i+1}块内容的answer")
                return
            _, length, rev_data = msg
            #log_message(log, f"RECV ANSWER {i+1}, length={length}")

            # 终端打印
            text = rev_data.decode('ascii', errors='replace')
            print(f"{i+1}: {text}")

            reversed_chunks.append(rev_data)

        # 最终文件应该是原始文件的全部反转
        # 因为我们是按顺序分块、每块反转，要实现整体反转，
        # 需要将反转后的块倒序拼接：最后一块的反转放在最前面。
        with open(output_file, 'wb') as f:
            for chunk in reversed(reversed_chunks):
                f.write(chunk)

        print(f"\n反转文件保存到{output_file}")

    sock.close()

if __name__ == "__main__":
    main()