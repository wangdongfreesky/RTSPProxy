import re
import socket
import threading
# 配置目标服务器的地址和端口
server_address = '192.168.37.20'
bad_server = '192.168.102.139'
server_port = 554
#从数据中提取域名或IP地址
def getaddress(response):
    # 定义正则表达式匹配 rtsp:// 后面的域名或IP地址，直到遇到冒号:
    pattern = r'rtsp://([^:]+)'   
    # 使用正则表达式查找匹配的内容
    match = re.search(pattern, response.decode('utf-8'))    
    # 判断并返回结果
    if match:
        return match.group(1)  # 返回匹配到的内容
    return "0" # 如果没有匹配到，返回“0”
#将数据中的ip地址，用ip地址串替换
def replaceip(response,ipv4_address):
    domain_pattern = r'rtsp://\b[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,}\b'
    pattern = r"rtsp://\d+\.\d+\.\d+\.\d+"
    tosend = re.sub(domain_pattern, "rtsp://"+ipv4_address, response.decode('utf-8'))
    tosend = re.sub(pattern,"rtsp://"+ipv4_address,tosend)
    return tosend.encode('utf-8')
#接收服务器数据处理后转发到客户端
def handle_StoC(client_socket,server_socket,clientaddress):
    #处理RTP流的转发
    print(f"开始转发数据")
    try:
        while True:           
            data = server_socket.recv(4096)
            if not data:
                break
            client_socket.sendall(data)
    except Exception as e:
        server_socket.close()
        client_socket.close()
        print(f"[!]收发错误！关闭连接: {e}")
#接收客户端请求数据处理后转发到服务器
def handle_CtoS(client_socket,server_socket,serveraddress):
    #处理RTP流的转发
    print(f"开始转发数据")
    try:
        while True:           
            data = client_socket.recv(4096)
            if not data:
                break
            server_socket.sendall(data)
    except Exception as e:
        server_socket.close()
        client_socket.close()
        print(f"[!]收发错误！关闭连接: {e}")
#生成二次握手请求(将OPIONS请求变为DESCRIBE请求)
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
#根据首发请求和查询服务器套接字获取新的目标服务器的地址以及新服务器的socket和首发响应。
def getnewserver(firstrequest,server_socket):    
    twotoserver = describe(firstrequest)
    print(f"继续发送服务器的二次请求:\n{twotoserver.decode('utf-8')}") 
    server_socket.sendall(twotoserver)
    response = server_socket.recv(4096)
    print(f"接收到的二次响应:\n{response.decode('utf-8')}")  
    targetaddress = getaddress(response)
    if targetaddress == bad_server:
        print(f"空的目标服务器关闭")
        return
    print(f"收到转跳命令后，用首次请求数据:\n{firstrequest}")    
    try:
        print(f"获取二次响应中的实际目标地址:\n{targetaddress}")
        onetoserver = replaceip(firstrequest,targetaddress)
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((targetaddress, server_port))
        print(f"重新连接发往目标服务器的请求为:\n{onetoserver.decode('utf-8')}")
        server_socket.sendall(onetoserver)
        response = server_socket.recv(4096)
        print(f"重新连接接收到新服务器响应为:\n{response.decode('utf-8')}")
    except Exception as e:
        server_socket.close()
        print(f"目标服务器无响应，关闭")
    return server_socket,response,targetaddress
#判断无会话ID，如果不包含session则返回True
def nonsession(response):
# 使用正则表达式匹配Session的值
    match = re.search(r"Session:\s*(\d+)", response.decode('utf-8'))
    if match:
        return False  # 如果找到Session，返回False，否则返回True
    return True  # 如果没有找到Session行，返回True
#处理客户端的请求与服务器的响应
def handle_entrance(client_socket):
    try:
        #默认目标地址为默认的服务器地址
        targetaddress = server_address
        #与目标服务器建立连接
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((targetaddress, server_port))
        ######首次接收客户端的请求
        for once in '1234':
            request = client_socket.recv(1024)
            print(f"接收到的客户端的请求为:\n{request.decode('utf-8')}")
            #提取客户端的访问域名或IP地址
            clientaddress = getaddress(request)
            #地址转换为目标服务器
            toserver = replaceip(request,targetaddress)
            ##首次将请求转发到目标 RTSP 服务器
            print(f"发往目标服务器的请求为:\n{toserver.decode('utf-8')}")
            server_socket.sendall(toserver)
            # 接收目标服务器的响应
            response = server_socket.recv(4096)
            print(f"接收到服务器响应为:\n{response.decode('utf-8')}")
            #如果不包含会话ID，则重新连接目标服务器
            if nonsession(response):
                print("该响应不包含会话ID，需要重新连接")
                #获取新的服务器套接字，响应数据，新的服务器地址
                server_socket, response, targetaddress = getnewserver(toserver,server_socket)
                print("新目标服务器已经重新连接")     
            # 将响应发送回客户端
            toclient = replaceip(response,clientaddress)       
            print(f"发往客户端的响应为:\n{toclient.decode('utf-8')}")
            client_socket.sendall(toclient)
        ##数据转发
        server_thread = threading.Thread(target=handle_StoC, args=(client_socket,server_socket,clientaddress))
        server_thread.start()
        client_thread = threading.Thread(target=handle_CtoS, args=(client_socket,server_socket,targetaddress))
        client_thread.start()
    except Exception as e:
        # 处理其他 socket 相关的异常
        print(f"连接失败")
        server_socket.close()
        client_socket.close()
        print(f"关闭连接")
def start_proxy():
    #代理服务器绑定554端口并进入监听模式
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(('0.0.0.0', 554))
    proxy_socket.listen(5)
    print("开始监听554端口")
    while True:
        client_socket, addr = proxy_socket.accept()
        print(f"连接 {addr}")
        proxy_handler = threading.Thread(target=handle_entrance, args=(client_socket,))
        proxy_handler.start()
if __name__ == '__main__':
    start_proxy()
