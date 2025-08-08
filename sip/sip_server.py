from message_generator.message_generator import MessageGenerator
from data_classes.params_classes import BaseMessageParams, RegisterParams, InfoParams, ReferParams
import socket
import time
import base64
import json
from message_decoder.header_decoder import parse_sip_message
from utils.utils import check_final_message
from rtp.rtp_endpoint import RtpEndpoint


class SIPServer:
    def __init__(self, user, local_ip, local_port, remote_ip, remote_port, local_rtp_port, remote_rtp_port):
        # 席位
        self.user = user
        self.password = self._base64_encode(user)
        # 服务端
        self.local_ip = local_ip
        self.local_port = local_port
        # 客户端
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        # 服务器
        self.server_ip = local_ip
        self.server_port = local_port

        self.allow = ['MESSAGE', 'REFER', 'INFO', 'NOTIFY', 'SUBSCRIBE', 'CANCEL', 'BYE', 'OPTIONS', 'ACK', 'INVITE']
        self.supported = ['100rel', 'replaces']

        self.channel_list = []  # 通道列表
        self.role_list = []  # 角色列表
        self.frequency_list = []  # 频率列表
        self.radio_list = []  # 电台列表

        # 当前选择
        # 加入检索电台是发送还是接收、是否可用的逻辑
        self.selected_role = None
        self.send_frequency = []
        self.recv_frequency = []
        self.send_radio = []
        self.recv_radio = []

        with open('./config/response_message_body.json', 'r') as file:
            self.data = json.load(file)

        # 状态
        self.status = "offline"  # 状态: "online", "offline", "busy"

        # PTT状态
        self.ptt = False

        # 消息生成器和RTP客户端
        self.message_generator = MessageGenerator()
        self.rtp_status = False
        self.rtp_endpoint = RtpEndpoint(local_ip, local_rtp_port, remote_ip, remote_rtp_port)

        # 创建UDP套接字
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.local_ip, self.local_port))
        print(f"SIP Client initialized on {self.local_ip}:{self.local_port}")

    def _base64_encode(self, data, urlsafe=False):
        """
        对字符串进行 Base64 编码
        """
        bytes_data = data.encode('utf-8')
        if urlsafe:
            encoded_bytes = base64.urlsafe_b64encode(bytes_data)
        else:
            encoded_bytes = base64.b64encode(bytes_data)
        return encoded_bytes.decode('utf-8')

    def _send_message(self, message):
        """发送SIP消息"""
        self.socket.sendto(message.encode(), (self.remote_ip, self.remote_port))

    def response_alive(self, recv_params):
        """回复心跳报文"""
        params = InfoParams(
            branch=recv_params.branch,
            call_id=recv_params.call_id,
            cseq=recv_params.cseq,
            tag=recv_params.tag,
            local_user=recv_params.server_user,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=recv_params.local_user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="response",
            message_type="INFO",
            subject=recv_params.subject,
            content_type="application/server_ip",
            content=self.data[recv_params.subject]['server_ip'],
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(msg)

    def response_register(self, recv_params):
        """回复注册报文"""
        params = RegisterParams(
            branch=recv_params.branch,
            call_id=recv_params.call_id,
            cseq=recv_params.cseq,
            tag=recv_params.tag,
            local_user=recv_params.server_user,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=recv_params.local_user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="response",
            message_type="REGISTER",
            expires=5,
            contact=True,
            content_type="application/role_info",
            content=self.data[recv_params.subject]['role_info'],
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(msg)

    def response_phone_btn(self, recv_params):
        """回复通道列表"""
        params = InfoParams(
            branch=recv_params.branch,
            call_id=recv_params.call_id,
            cseq=recv_params.cseq,
            tag=recv_params.tag,
            local_user=recv_params.server_user,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=recv_params.local_user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="response",
            message_type="INFO",
            content_type="application/phone_bt_info",
            content=self.data[recv_params.subject]['phone_bt_info'],
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(msg)

    def response_frequency_btn(self, recv_params):
        """回复频率列表"""
        cseq = 1025
        for key, value in self.data[recv_params.subject].items():
            params = InfoParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="INFO",
                content_type="application/frequency_bt_info",
                content=value,
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)
            cseq += 1

    def response_radio_btn(self, recv_params):
        """回复电台列表"""
        cseq = 1793
        for key, value in self.data[recv_params.subject].items():
            params = InfoParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="INFO",
                content_type="application/radio_bt_info",
                content=value,
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)
            cseq += 1

    def response_function_btn(self, recv_params):
        """获取功能列表"""
        cseq = 257
        for key, value in self.data[recv_params.subject].items():
            params = InfoParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=recv_params.cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="INFO",
                content_type="application/func_bt_info",
                content=value,
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)

    def response_all_frequency_btn(self, recv_params):
        """获取所有频率"""
        cseq = 1025
        for key, value in self.data[recv_params.subject].items():
            params = InfoParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="INFO",
                content_type="application/frequency_bt_info",
                content=value,
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)
            cseq += 1   

    def response_radio(self, recv_params):
        """回复选中电台"""
        if recv_params.message_type == "INVITE":
            # 100 Trying
            params = BaseMessageParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=recv_params.cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="INVITE",
                status_code=100,
                reason_phrase="Trying",
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)
            self.rtp_endpoint.start()
            params = BaseMessageParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=recv_params.cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="INVITE",
                subject=recv_params.subject,
                contact=True,
                allow=self.allow,
                supported=self.supported,
                content_type="application/sdp",
                content=self._generate_default_sdp(),
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)
        elif recv_params.message_type == "REFER":
            params = BaseMessageParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=recv_params.cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="REFER",
                subject=recv_params.subject,
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)

    def response_bye(self, recv_params):
        """回复退出电台"""
        if recv_params.message_type == "REFER":
            params = BaseMessageParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=recv_params.cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="REFER",
                # subject=recv_params.subject,
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)
        elif recv_params.message_type == "BYE":
            params = BaseMessageParams(
                branch=recv_params.branch,
                call_id=recv_params.call_id,
                cseq=recv_params.cseq,
                tag=recv_params.tag,
                local_user=recv_params.server_user,
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=recv_params.local_user,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="response",
                message_type="BYE",
                subject=recv_params.subject,
            )
            msg = self.message_generator.generate_message(params)
            self._send_message(msg)
            self.rtp_endpoint.stop()

    def _generate_default_sdp(self):
        """生成符合示例格式的SDP内容"""
        return (
            "v=0\r\n"
            f"o=SELUS 2890844527 1 IN IP4 {self.local_ip}\r\n"
            "s=Sip Call\r\n"
            f"c=IN IP4 {self.local_ip}\r\n"
            "t=0 0\r\n"
            "m=audio 5200 RTP/AVP 8\r\n"
            "a=rtpmap:8 PCMA/8000\r\n"
            "a=sendrecv\r\n"
        )

    def receive_message(self):
        while True:
            data, addr = self.socket.recvfrom(4096)
            message = data.decode('utf-8')
            print(f"Received message from {addr}:\n{message}")
            # 例如根据消息类型调用不同的处理方法
            self.handle_message(message)

    def handle_message(self, message):
        header_part, _, body = message.partition('\r\n\r\n')
        recv_params = parse_sip_message(header_part)
        print(recv_params.message_type)
        print(recv_params.subject)
        if recv_params.subject == 'vcu_login' or recv_params.subject == 'vcu_logout':
            self.response_alive(recv_params)
        elif recv_params.subject == 'vcu_register':
            self.response_register(recv_params)
        elif recv_params.subject == 'vcu_phone':
            self.response_phone_btn(recv_params)
        elif recv_params.subject == 'vcu_frequency':
            self.response_frequency_btn(recv_params)
        elif recv_params.subject == 'vcu_radio':
            self.response_radio_btn(recv_params)
        elif recv_params.subject == 'vcu_function':
            self.response_function_btn(recv_params)
        elif recv_params.subject == 'vcu_all_frequency':
            self.response_all_frequency_btn(recv_params)
        elif recv_params.subject == 'radio':
            if recv_params.message_type.upper() == "INVITE" or (
                    recv_params.message_type.upper() == "REFER" and recv_params.method is None):
                self.response_radio(recv_params)
            elif recv_params.message_type.upper() == "BYE" or (
                    recv_params.message_type.upper() == "REFER" and recv_params.method == "BYE"):
                self.response_bye(recv_params)