from message_generator.message_generator import MessageGenerator
from data_classes.params_classes import BaseMessageParams, RegisterParams, InfoParams, ReferParams
import socket
import time
import base64
from message_decoder.role_info_decoder import RoleInfo
from message_decoder.tel_btn_info_decoder import TelBtnInfo
from message_decoder.freq_btn_info_decoder import FreqBtnInfo
from message_decoder.radio_btn_info_decoder import RadioInfo
from message_decoder.fun_btn_info_decoder import MyFunBtnInfo
from message_decoder.header_decoder import parse_sip_message
from utils.utils import check_final_message
from data_classes.comm_classes import Radio
from collections import deque
from rtp.rtp_endpoint import RtpEndpoint


# 待加入功能：接收回复后发送
# 超时重传
class SIPClient:
    def __init__(self, user, local_ip, local_port, remote_ip, remote_port, local_rtp_port, remote_rtp_port):
        # 席位
        self.user = user
        self.password = self._base64_encode(user)
        # 客户端
        self.local_ip = local_ip
        self.local_port = local_port
        # 服务端
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        # 服务器
        self.server_ip = remote_ip
        self.server_port = remote_port
        self.allow = ['MESSAGE', 'REFER', 'INFO', 'NOTIFY', 'SUBSCRIBE', 'CANCEL', 'BYE', 'OPTIONS', 'ACK', 'INVITE']
        self.supported = ['100rel', 'replaces']
        self.channel_list = []  # 通道列表
        self.role_list = []  # 角色列表
        self.frequency_dict = {}  # 频率列表
        self.radio_dict = {}  # 电台列表
        # 当前选择
        # 加入检索电台是发送还是接收、是否可用的逻辑
        self.selected_role = None
        # self.send_frequency = []
        # self.recv_frequency = []
        self.send_radio = []
        self.recv_radio = []
        # self.selected = False
        # 控制报文收发时序逻辑
        self.cseq_history = deque(maxlen=100)  # 消息历史记录
        self.message_queue = deque()  # 待发送消息队列
        self.processing_message = False  # 消息处理状态标志
        self.last_cseq = 0  # 最后使用的CSeq序号
        # 状态
        self.status = "offline"  # 状态: "online", "offline", "busy"
        # PTT状态
        self.ptt = False
        # 消息生成器和RTP客户端
        self.message_generator = MessageGenerator()
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

    # def _get_next_cseq(self):
    #     """获取下一个CSeq序号"""
    #     self.last_cseq += 1
    #     return self.last_cseq

    def _send_message(self, cseq, params, message):
        """发送SIP消息(带时序控制)"""
        params.cseq = cseq
        # 记录发送历史
        if len(self.cseq_history) == 0 and not self.processing_message:
            print("没有待发送消息，直接发送")
            self._send_message_now(params, message)
            return
        # 如果正在处理消息，则加入队列
        else:
            self.message_queue.append((params, message))
            print(f"消息已加入队列(CSeq: {params.cseq})")
            return

    def _send_message_now(self, params, message):
        """实际发送消息"""
        try:
            self.socket.sendto(message.encode(), (self.remote_ip, self.remote_port))
            if params.message_type != "ACK":
                self.cseq_history.append((params.cseq, params))
        except Exception as e:
            print(f"发送消息出错: {e}")

    # def _process_message_queue(self):
    #     """处理消息队列中的待发消息"""
    #     while len(self.message_queue) == 0 and not self.processing_message:
    #         params, message = self.message_queue.popleft()
    #         self._send_message_now(params, message)
    #         return

    def keep_alive(self):
        """心跳报文"""
        while len(self.cseq_history) > 0:
            pass
        params = InfoParams(
            local_user=self.user,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=self.user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="request",
            message_type="INFO",
            expires=5,
        )
        if self.status == "offline":
            params.subject = "vcu_logout"
        else:
            params.subject = "vcu_login"
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def register(self):
        """注册报文"""
        while len(self.cseq_history) > 0:
            pass
        params = RegisterParams(
            local_user=self.user,
            password=self.password,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=self.user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="request",
            message_type="REGISTER",
            subject="vcu_register",
            expires=5,
            cwp=self.user,
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def get_phone_btn(self):
        """获取通道列表"""
        while len(self.cseq_history) > 0:
            pass
        params = InfoParams(
            local_user=self.user,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=self.user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="request",
            message_type="INFO",
            subject="vcu_phone",
            roleid=self.selected_role if self.selected_role else None,
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def get_frequency_btn(self):
        """获取频率列表"""
        while len(self.cseq_history) > 0:
            pass
        params = InfoParams(
            local_user=self.user,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=self.user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="request",
            message_type="INFO",
            subject="vcu_frequency",
            roleid=self.selected_role if self.selected_role else None,
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def get_radio_btn(self):
        """获取电台列表"""
        while len(self.cseq_history) > 0:
            pass
        params = InfoParams(
            local_user=self.user,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=self.user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="request",
            message_type="INFO",
            subject="vcu_radio",
            roleid=self.selected_role if self.selected_role else None,
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def get_function_btn(self):
        """获取功能列表"""
        while len(self.cseq_history) > 0:
            pass
        params = InfoParams(
            local_user=self.user,
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=self.user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="request",
            message_type="INFO",
            subject="vcu_function",
            roleid=self.selected_role if self.selected_role else None,
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def get_all_frequency_btn(self):
        """获取所有频率"""
        while len(self.cseq_history) > 0:
            pass
        params = InfoParams(
            local_user=self.channel_list[0],
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=self.user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="request",
            message_type="INFO",
            subject="all_freq",
            roleid=self.selected_role if self.selected_role else None,
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def select_radio(self, channel):
        while len(self.cseq_history) > 0:
            pass
        if len(self.send_radio) + len(self.recv_radio) == 0:
            print("第一次选中电台")
            params = BaseMessageParams(
                local_user=self.channel_list[2],
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=channel,
                server_ip=self.server_ip,
                server_port=self.server_port,
                message_type="INVITE",
                method_type="request",
                subject="radio",
                expires=5,
                contact=True,
                allow=self.allow,
                supported=self.supported,
                content_type="application/sdp",
                content=self._generate_default_sdp(),
            )
        else:
            print("再次选中电台")
            params = ReferParams(
                local_user=self.channel_list[2],
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=channel,
                server_ip=self.server_ip,
                server_port=self.server_port,
                message_type="REFER",
                method_type="request",
                subject="radio",
                expires=5,
                refer_to=True,
                refered_by=True,
            )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def ack(self):
        """发送ACK报文"""
        params = BaseMessageParams(
            local_user=self.channel_list[2],
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=self.user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            method_type="request",
            message_type="ACK",
            subject="radio",
            allow=self.allow,
            supported=self.supported,
        )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def bye(self, channel):
        """退出电台选中"""
        while len(self.cseq_history) > 0:
            pass
        if len(self.send_radio) + len(self.recv_radio) > 0:
            print("退出电台选中")
            params = ReferParams(
                local_user=self.channel_list[2],
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=channel,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="request",
                message_type="REFER",
                subject="radio",
                expires=5,
                refer_to=True,
                refered_by=True,
                method="BYE",
            )
        else:
            print("退出最后一个电台")
            params = BaseMessageParams(
                local_user=self.channel_list[2],
                local_ip=self.local_ip,
                local_port=self.local_port,
                server_user=channel,
                server_ip=self.server_ip,
                server_port=self.server_port,
                method_type="request",
                message_type="BYE",
                subject="radio",
                expires=5,
            )
        msg = self.message_generator.generate_message(params)
        self._send_message(self.message_generator.cseq, params, msg)

    def key_up(self):
        """PTT按下"""
        pass

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

    # def parase_message(self, subject, message_body):
    #     if subject == "vcu_register":
    #         info = RoleInfo().parse(message_body)
    #     elif subject == "vcu_phone":
    #         info = TelBtnInfo.parse(message_body)
    #     elif subject == "vcu_frequency":
    #         info = FreqBtnInfo.parse(message_body)
    #     elif subject == "vcu_radio":
    #         info = RadioInfo.parse(message_body)
    #     elif subject == "vcu_function":
    #         info = MyFunBtnInfo.parse(message_body)
    #     else:
    #         print(f"未知主题: {subject}")
    #         return
    #     return info

    def receive_message(self):
        while True:
            data, addr = self.socket.recvfrom(10240)  # 缓冲区大小设为2048字节
            message = data.decode('utf-8')
            print(f"Received message from {addr}:\n{message}")
            # 例如根据消息类型调用不同的处理方法
            self.handle_message(message)

    def handle_message(self, message):
        """处理收到的SIP消息"""
        self.processing_message = True
        handle_status = False
        try:
            header_part, _, body = message.partition('\r\n\r\n')
            recv_params = parse_sip_message(header_part)
            if recv_params.status_code == 200:
                handle_status = self._handle_200_response(recv_params, body)
                if handle_status:
                    print(f"处理消息成功: (CSeq: {recv_params.cseq})")
                    self.cseq_history.popleft()
            else:
                print(f"收到非200响应: {recv_params.status_code}")
        except Exception as e:
            print(f"处理消息出错: {e}")
        finally:
            self.processing_message = not handle_status
            # self._process_message_queue()

    def _handle_200_response(self, recv_params, body):
        """处理200 OK响应"""
        # 当前发送消息
        cseq, params = self.cseq_history[0] if len(self.cseq_history) > 0 else (None, None)
        # 根据报文类型处理
        # 心跳报文
        if cseq == recv_params.cseq and params.subject == "vcu_logout":
            self.status = "online"
            print("状态变更为: online")
            return True
        # 注册报文
        elif cseq == recv_params.cseq and params.subject == "vcu_register":
            info = RoleInfo().parse(body)
            self.channel_list = info.ChannelNum
            print(f"注册成功，通道列表: {self.channel_list}")
            return True
        # 按键报文
        elif params.subject == "vcu_phone" and recv_params.content_type == "application/phone_bt_info":
            info = TelBtnInfo.parse(body)
            print("收到电话按钮信息:")
            for info_t in info:
                print(f"  - {info_t}")
            if check_final_message(recv_params.cseq):
                return True
            else:
                return False
        elif params.subject == "vcu_frequency" and recv_params.content_type == "application/frequency_bt_info":
            info = FreqBtnInfo.parse(body)
            print("收到频率按钮信息:")
            for info_t in info:
                print(f"  - {info_t}")
            if check_final_message(recv_params.cseq):
                return True
            else:
                return False
        elif params.subject == "vcu_radio" and recv_params.content_type == "application/radio_bt_info":
            info = RadioInfo.parse(body)
            print("收到电台信息:")
            for info_t in info:
                radio = Radio(
                    freq=str(info_t.szFrequency.decode('utf-8')),
                    type=info_t.iRSType,
                    avail=info_t.iIsCan,
                )
                self.radio_dict[str(info_t.szCode.decode('utf-8'))] = radio
                print(f"  - 电台{info_t.szCode}: 频率{radio.freq}, 类型{radio.type}")
            if check_final_message(recv_params.cseq):
                return True
            else:
                return False
        # 电台操控报文
        elif cseq == recv_params.cseq and params.subject == "radio":
            self._handle_radio_response(params)
            return True
        else:
            return False

    def _handle_radio_response(self, params):
        """处理电台相关响应"""
        port = params.server_user
        if params.message_type.upper() == 'INVITE':
            if self.radio_dict[port].type == 0:
                self.send_radio.append(port)
            else:
                self.recv_radio.append(port)
            self.rtp_endpoint.start()
            self.ack()
        elif (params.message_type.upper() == 'REFER' and
              getattr(params, 'method', None) is None):
            print(f'加入电台: {port}')
            if self.radio_dict[port].type == 0:
                self.send_radio.append(port)
            else:
                self.recv_radio.append(port)
        elif (params.message_type.upper() == 'REFER' and
              getattr(params, 'method', None) == 'BYE'):
            print(f'离开电台: {port}')
            if port in self.send_radio:
                self.send_radio.remove(port)
            elif port in self.recv_radio:
                self.recv_radio.remove(port)
        elif params.message_type.upper() == 'BYE':
            print(f'离开电台: {port}')
            if port in self.send_radio:
                self.send_radio.remove(port)
            elif port in self.recv_radio:
                self.recv_radio.remove(port)
            self.rtp_endpoint.stop()