import socket
import struct
import sys
import random
import time
from datetime import datetime

# 报文类型
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

# 接收数据
def recv_exactly(sock, n: int) -> bytes:
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed unexpectedly")
        data += chunk
    return data

# 解析报文
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


# 生成块长度
def generate_chunk_sizes(file_len, lmin, lmax, seed):
    random.seed(seed)
    chunks = []
    remaining = file_len
    while remaining > 0:
        if remaining > lmax:
            chunk = random.randint(lmin, lmax)
        else:
            chunk = remaining
        chunks.append(chunk)
        remaining -= chunk
    return chunks

def log_message(file, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    file.write(f"[{timestamp}] {msg}\n")
    file.flush()

def main():
    if len(sys.argv) != 8:
        print("Usage: python reversetcpclient.py <ip地址> <端口号> <最小值> <最大值> <种子> <输入文件> <输出文件>")
        sys.exit(1)

    server_ip   = sys.argv[1]
    port        = int(sys.argv[2])
    lmin        = int(sys.argv[3])
    lmax        = int(sys.argv[4])
    seed        = int(sys.argv[5])
    input_file = sys.argv[6]
    output_file = sys.argv[7]

    #读取文件
    with open(input_file, 'rb') as f:
        file_data = f.read()
    file_len = len(file_data)

    #分块
    chunks = generate_chunk_sizes(file_len, lmin, lmax, seed)
    n = len(chunks)
    print(f"文件为{file_len}bytes,被分成{n}块")
    for i, size in enumerate(chunks):
        print(f"第{i+1}块大小为: {size} bytes")

    #连接服务器
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, port))

    with open("run_log.txt", "a", encoding="utf-8") as log:
        #Initialization
        sock.sendall(create_init_message(n))
        log_message(log, f"SEND init to {server_ip}:{port}, N={n}")

        #agree
        msg = parse_message(sock)
        if not msg or msg[0] != TYPE_AGREE:
            print("没有收到server的agree")
            return
        log_message(log, f"RECV agree from {server_ip}:{port}")

        reversed_chunks = []
        offset = 0

        for i, chunk_size in enumerate(chunks):
            data = file_data[offset:offset+chunk_size]
            offset += chunk_size

            #reverseRequest
            sock.sendall(create_request_message(data))
            log_message(log, f"SEND request {i+1}, length={chunk_size+6}")
            #人为延迟
            time.sleep(0.5)

            #reverseAnswer
            msg = parse_message(sock)
            if not msg or msg[0] != TYPE_ANSWER:
                print(f"没有收到第{i+1}块内容的answer")
                return
            _, length, rev_data = msg
            log_message(log, f"RECV answer {i+1}, length={length+6}")

            text = rev_data.decode('ascii', errors='replace')
            print(f"{i+1}: {text}")

            reversed_chunks.append(rev_data)


        with open(output_file, 'wb') as f:
            for chunk in reversed(reversed_chunks):
                f.write(chunk)

        print(f"\n反转文件保存到{output_file}")

    sock.close()

if __name__ == "__main__":
    main()