from sip.sip_server import SIPServer
import json
import threading
import time

if __name__ == '__main__':
    with open('./config/comm_config.json', 'r') as file:
        config = json.load(file)

    sip_server = SIPServer(
        user='bxp',
        local_ip=config['server']['ip'],
        local_port=config['server']['port'],
        remote_ip=config['client']['ip'],
        remote_port=config['client']['port'],
        local_rtp_port=config['server']['rtp_port'],
        remote_rtp_port=config['client']['rtp_port'],
    )

    # 启动服务端的消息接收线程
    server_thread = threading.Thread(target=sip_server.receive_message)
    server_thread.daemon = True
    server_thread.start()

    # 保持程序运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")


