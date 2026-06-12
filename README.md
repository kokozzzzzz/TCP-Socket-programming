TCP Socket 文本反转实验
========================
运行环境：
- 宿主机：Windows 11，Python 3.12
- 虚拟机：Ubuntu  (VMware NAT)，Python 3.12

使用步骤：
1. 在 Ubuntu 上启动服务器：
   python3 reversetcpserver.py 1234
2. 在宿主机上准备输入文件 input.txt（纯英文ASCII）
3. 在宿主机运行客户端：
   python reversetcpclient.py <虚拟机IP> <端口号> <Lmin> <Lmax> <种子> <输入文件> <输出文件>
   例：python reversetcpclient.py 192.168.126.130 1234 10 50 42 input.txt output.txt
4. 客户端终端打印每块反转内容，并生成 output.txt（整体反转文件）和 run_log.txt（日志）。
5. 用 Wireshark 抓取 VMnet8 网卡，验证报文。
