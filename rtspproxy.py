import re
import socket
import threading
# 配置目标服务器的地址和端口
server_address = '192.168.37.20'
server_port = 554
#判断响应中是否包含转跳
def ismoved(response):
    if "RTSP/1.0 302 Moved Temporarily" in response.decode('utf-8'):
        print("字符串中包含 'RTSP/1.0 302 Moved Temporarily'")
        return True
    else:
        print("字符串中不包含 'RTSP/1.0 302 Moved Temporarily'")
        return False
#从数据中提取域名或IP地址
def getaddress(response):
    # 定义正则表达式匹配 rtsp:// 后面的域名或IP地址，直到遇到 :
    pattern = r'rtsp://([^:]+)'   
    # 使用正则表达式查找匹配的内容
    match = re.search(pattern, response.decode('utf-8'))    
    # 判断并返回结果
    if match:
        return match.group(1)  # 返回匹配到的内容
    else:
        # 如果没有匹配到，返回“不存在”
        return "不存在域名或IP地址"
#将数据中的ip地址，用ip地址串替换
def convert(response,ipv4_address):
    domain_pattern = r'rtsp://\b[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,}\b'
    pattern = r"rtsp://\d+\.\d+\.\d+\.\d+"
    tosend = re.sub(domain_pattern, "rtsp://"+ipv4_address, response.decode('utf-8'))
    tosend = re.sub(pattern,"rtsp://"+ipv4_address,tosend)
    print(f"转换后的目标请求:\n{tosend}")
    return tosend.encode('utf-8')
#TCP数据流转发
def handle_forward(client_socket,server_socket):
    """处理RTP流的转发"""
    try:
        while True:
            try:
                data = server_socket.recv(4096)
                if not data:
                    break
                client_socket.sendall(data)
                print(f"[+] 转发RTP数据 {len(data)} 字节 从 {server_socket.getpeername()} 到 {client_socket.getpeername()}")
            except OSError as e:
                print(f"[!] 转发RTP数据发生错误: {e}")
                break
    except Exception as e:
        print(f"[!] handle_forward中发生错误: {e}")
    finally:
        try:
            server_socket.close()
        except OSError:
            pass
        try:
            client_socket.close()
        except OSError:
            pass
        print(f"[!] 关闭RTP连接")
#将包含转跳地址的服务器响应，重新翻译成请求
def translation(request, response):
    # 正则表达式匹配RTSP URL
    rtsp_url_pattern = r"rtsp://[^\s]+" 
    # 从response中提取RTSP URL
    response_match = re.search(rtsp_url_pattern, response.decode('utf-8'))
    if response_match:
        new_rtsp_url = response_match.group(0)
        
        # 在request中替换RTSP URL
        request_match = re.search(rtsp_url_pattern, request.decode('utf-8'))
        if request_match:
            old_rtsp_url = request_match.group(0)
            # 替换request中的RTSP URL
            new_request = request.decode('utf-8').replace(old_rtsp_url, new_rtsp_url)
            return new_request.encode('utf-8')
        else:
            print("未在请求字符串中找到RTSP URL")
    else:
        print("未在响应字符串中找到RTSP URL")
    return request
#重新连接新的目标服务器,返回新的目标服务器的socket和包含转跳响应的response
def reconnect(firstrequest,response):
    targetaddress= getaddress(response)
    print(f"获取二次响应中的实际目标地址:\n{targetaddress}")
    print(f"获取二次响应中的实际目标地址:\n{targetaddress}")
    onetoserver = translation(firstrequest,response)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.connect((targetaddress, server_port))
    except Exception as e:
        server_socket.close()
        return
    print(f"重新连接发往目标服务器的请求为:\n{onetoserver.decode()}")
    server_socket.sendall(onetoserver)
    response = server_socket.recv(4096)
    print(f"重新连接接收到服务器响应为:\n{response.decode()}")
    if ismoved(response):
        server_socket,response = reconnect(firstrequest,response)
    else:        
        return server_socket,response  
#生成二次握手请求
def describe(firstrequest):
    # 新的 IP 地址和端口号
    new_ip_port = server_address + ":" + str(server_port)
    # 使用正则表达式替换 IP 地址和端口号部分
    original_string = re.sub(r'rtsp://\b[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,}\b:\d+', f'rtsp://{new_ip_port}', firstrequest.decode('utf-8'))
    original_string = re.sub(r'rtsp://\d+\.\d+\.\d+\.\d+:\d+', f'rtsp://{new_ip_port}', original_string)
    # 将字符串按行分割
    lines = original_string.split('\n')
    # 替换第一行的 OPTIONS 为 DESCRIBE
    lines[0] = lines[0].replace('OPTIONS', 'DESCRIBE')
    # 更新 CSeq 的值为 2
    lines[1] = lines[1].replace('CSeq: 1', 'CSeq: 2')
    # 添加 Accept: application/sdp 行
    lines.insert(1, 'Accept: application/sdp')
    # 将修改后的行重新组合为字符串
    new_string = '\n'.join(lines)
    return new_string.encode('utf-8')
#获取目标服务器的会话，返回目标服务器的socket，以及二次响应和包含转跳的旧的服务器的响应
def getserver(firstrequest,server_socket):    
    twotoserver = describe(firstrequest)
    print(f"继续发送服务器的二次请求:\n{twotoserver.decode('utf-8')}") 
    server_socket.sendall(twotoserver)
    response = server_socket.recv(4096)
    print(f"接收到的二次响应:\n{response.decode('utf-8')}")
    if ismoved(response):
        print(f"收到转跳命令后，用首次请求数据:\n{firstrequest}")
        targetsponse = response
        try:
            server_socket, response = reconnect(firstrequest,response)
        except Exception as e:
            return
    return server_socket,response,targetsponse
#判断是否是首次握手请求
def iscseqone(request):
    # 使用正则表达式匹配CSeq的值
    match = re.search(r"CSeq:\s*(\d+)", request.decode('utf-8'))
    if match:
        cseq_value = int(match.group(1))  # 提取CSeq的值并转换为整数
        return cseq_value == 1  # 如果值为1，返回True，否则返回False
    return False  # 如果没有找到CSeq行，返回False 
#判断是否是第四次响应
def iscseqfour(response):
    # 使用正则表达式匹配CSeq的值
    match = re.search(r"CSeq:\s*(\d+)", response.decode('utf-8'))
    if match:
        cseq_value = int(match.group(1))  # 提取CSeq的值并转换为整数
        return cseq_value == 4  # 如果值为4，返回True，否则返回False
    return False  # 如果没有找到CSeq行，返回False
#判断无会话ID，如果不包含session则返回True
def nonsession(response):
# 使用正则表达式匹配Session的值
    match = re.search(r"Session:\s*(\d+)", response.decode('utf-8'))
    if match:
        Session_value = int(match.group(1))  # 提取CSeq的值并转换为整数
        return False  # 如果值为4，返回False，否则返回True
    return True  # 如果没有找到Session行，返回True
#处理客户端的请求与服务器的响应
def handle_client(client_socket):
    try:
        #默认目标地址为默认的服务器地址
        targetaddress = server_address
        #初始化目标服务器的响应为一个不生效的字符串
        targetsponse = server_address.encode('utf-8')
        #与目标服务器建立连接
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((targetaddress, server_port))
        ######首次接收客户端的请求
        while True:
            request = client_socket.recv(1024)
            print(f"接收到的客户端的请求为:\n{request.decode('utf-8')}")
            #提取客户端的访问域名或IP地址
            sourceaddress = getaddress(request)
            if iscseqone(request):
                firstrequest = request
            #地址转换为目标服务器
            toserver = convert(request,targetaddress)
            toserver = translation(toserver,targetsponse)
            ##首次将请求转发到目标 RTSP 服务器
            print(f"发往目标服务器的请求为:\n{toserver.decode()}")
            server_socket.sendall(toserver)
            # 接收目标服务器的响应
            response = server_socket.recv(4096)
            print(f"接收到服务器响应为:\n{response.decode()}")
            #如果不包含会话ID，则重新连接目标服务器
            if nonsession(response):
                print("该响应不包含会话ID，需要重新连接")
                #更换目标地址
                server_socket, response, targetsponse = getserver(firstrequest,server_socket)
                targetaddress = getaddress(targetsponse)
                print(f"接收到新服务器响应为:\n{targetsponse.decode()}")
                print(f"接收到新服务器地址为:\n{targetaddress}")
                print("目标重新连接")     
            # 将响应发送回客户端
            toclient = convert(response,sourceaddress)       
            print(f"发往客户端的响应为:\n{toclient.decode()}")
            client_socket.sendall(toclient)
            #如果是四次握手成功，则跳出循环，新开一个线程处理数据流转发
            if iscseqfour(response):
                break
        ##数据转发
        server_thread = threading.Thread(target=handle_forward, args=(client_socket,server_socket))
        server_thread.start()
    except Exception as e:
        # 处理其他 socket 相关的异常
        print(f"连接失败")
        server_socket.close()
        client_socket.close()
        print(f"关闭连接")
        return
def start_proxy():
    #代理服务器绑定554端口并进入监听模式
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(('0.0.0.0', 554))
    proxy_socket.listen(5)
    print("开始监听554端口")
    while True:
        client_socket, addr = proxy_socket.accept()
        print(f"连接 {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()
if __name__ == '__main__':
    start_proxy()
