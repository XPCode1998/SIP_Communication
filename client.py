from sip.sip_client import SIPClient
import json
import threading
import time

if __name__ == '__main__':
    with open('./config/comm_config.json', 'r') as file:
        config = json.load(file)

    sip_client = SIPClient(
        user='bxp',
        local_ip=config['client']['ip'],
        local_port=config['client']['port'],
        remote_ip=config['server']['ip'],
        remote_port=config['server']['port'],
        local_rtp_port=config['client']['rtp_port'],
        remote_rtp_port=config['server']['rtp_port'],
    )

    # 启动客户端的消息接收线程
    client_thread = threading.Thread(target=sip_client.receive_message)
    client_thread.daemon = True
    client_thread.start()
    sip_client.keep_alive()
    sip_client.register()
    sip_client.get_frequency_btn()
    sip_client.get_radio_btn()
    sip_client.select_radio('5000')
    sip_client.select_radio('5000')
    sip_client.bye('5001')
    sip_client.bye('5000')

    
    # 保持程序运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
