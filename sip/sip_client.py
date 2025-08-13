from message_generator.message_generator import MessageGenerator
from data_classes.params_classes import BaseMessageParams, RegisterParams, InfoParams, ReferParams
import socket
import time
import base64
from message_decoder.role_info_decoder import RoleInfo
from message_decoder.tel_btn_info_decoder import TelBtnInfo
from message_decoder.freq_btn_info_decoder import FreqBtnInfo
from message_decoder.radio_btn_info_decoder import RadioInfo
from message_decoder.header_decoder import parse_sip_message
from utils.utils import check_final_message
from data_classes.comm_classes import Radio
from collections import deque
from rtp.rtp_endpoint import RtpEndpoint
import re


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

        # 报文相关
        self.cseq = 0
        self.allow = ['MESSAGE', 'REFER', 'INFO', 'NOTIFY', 'SUBSCRIBE', 'CANCEL', 'BYE', 'OPTIONS', 'ACK', 'INVITE']
        self.supported = ['100rel', 'replaces']

        # 服务器信息
        self.channel_list = []  # 通道列表
        self.role_list = []  # 角色列表
        self.frequency_list = []  # 频率列表
        self.radio_dict = {}  # 电台列表

        # 当前状态
        self.status = "offline"  # 状态: "online", "offline", "busy"
        self.selected_role = None
        self.send_radio = []
        self.recv_radio = []
        # 加入检索电台是发送还是接收、是否可用的逻辑

        # 控制报文收发时序逻辑
        self.send_history = deque(maxlen=100)  # 消息历史记录
        self.latest_cseq = -1  # 最新发送报文的Cseq

        # 超时重传逻辑
        self.retry_timeout = 5  # 重传超时时间
        self.max_retries = 3  # 最大重传次数

        # PTT状态
        self.ptt = False

        # 消息生成器和RTP客户端
        self.message_generator = MessageGenerator()
        self.local_rtp_port = local_rtp_port
        self.rtp_endpoint = None

        # 创建UDP套接字
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.local_ip, self.local_port))
        print(f"SIP Client initialized on {self.local_ip}:{self.local_port}")

        self.is_switch_radio = False

    def _cseq_increment(self):
        """递增CSeq序号"""
        self.cseq += 1
        return self.cseq

    def _base64_encode(self, data, urlsafe=False):
        """对字符串进行 Base64 编码"""
        bytes_data = data.encode('utf-8')
        if urlsafe:
            encoded_bytes = base64.urlsafe_b64encode(bytes_data)
        else:
            encoded_bytes = base64.b64encode(bytes_data)
        return encoded_bytes.decode('utf-8')

    def _send_message(self, params):
        """发送SIP消息(带时序控制)"""
        message = self.message_generator.generate_message(params)
        # 待修改，将ACK类型的报文改为特殊回复
        # 记录发送历史
        if params.message_type == 'ACK':
            self.socket.sendto(message.encode(), (self.remote_ip, self.remote_port))
        elif len(self.send_history) == 0:
            send_time = time.time()
            retry_count = 0
            self.send_history.append((params, message, send_time, retry_count))
            self.socket.sendto(message.encode(), (self.remote_ip, self.remote_port))

    def _wait_response(self):
        while len(self.send_history) > 0:
            pass
        return

    def keep_alive(self):
        """心跳报文"""
        self._wait_response()
        params = InfoParams(
            cseq=self._cseq_increment(),
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
        self._send_message(params)

    def register(self):
        """注册报文"""
        self._wait_response()
        params = RegisterParams(
            cseq=self._cseq_increment(),
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
        self._send_message(params)

    def get_phone_btn(self):
        """获取通道列表"""
        self._wait_response()
        params = InfoParams(
            cseq=self._cseq_increment(),
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
        self._send_message(params)

    def get_frequency_btn(self):
        """获取频率列表"""
        self._wait_response()
        params = InfoParams(
            cseq=self._cseq_increment(),
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
        self._send_message(params)

    def get_radio_btn(self):
        """获取电台列表"""
        self._wait_response()
        params = InfoParams(
            cseq=self._cseq_increment(),
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
            content_type="application/frequency",
            content="+".join(self.frequency_list),
        )
        self._send_message(params)

    def get_function_btn(self):
        """获取功能列表"""
        self._wait_response()
        params = InfoParams(
            cseq=self._cseq_increment(),
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
        self._send_message(params)

    def get_all_frequency_btn(self):
        """获取所有频率"""
        self._wait_response()
        params = InfoParams(
            cseq=self._cseq_increment(),
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
        self._send_message(params)

    def is_switch_radio(self, channel):
        need_switch = False
        send_channel = self.send_radio[0] if len(self.send_radio) > 0 else None
        recv_channel = self.recv_radio[0] if len(self.recv_radio) > 0 else None
        # 检查发送频道频率是否不同
        if send_channel and self.radio_dict[channel].freq != self.radio_dict[send_channel].freq:
            need_switch = True
        # 检查接收频道频率是否不同
        if recv_channel and self.radio_dict[channel].freq != self.radio_dict[recv_channel].freq:
            need_switch = True
        if need_switch:
            print('切换电台')
            # 处理发送频道
            if send_channel:
                self.is_switch_radio = True
                self.bye(send_channel)
                self.is_switch_radio = False
            # 处理接收频道
            if recv_channel:
                self.is_switch_radio = True
                self.bye(recv_channel)
                self.is_switch_radio = False
            return True
        else:
            return False

    def select_radio(self, channel):
        self._wait_response()
        # 首次选中电台
        if len(self.send_radio) + len(self.recv_radio) == 0:
            params = BaseMessageParams(
                cseq=self._cseq_increment(),
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
        # 再次选中电台
        else:
            if self.is_switch_radio(channel):
                self._wait_response()
            params = ReferParams(
                cseq=self._cseq_increment(),
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
        self._send_message(params)

    def ack(self, send_params, recv_params):
        """发送ACK报文"""
        params = BaseMessageParams(
            cseq=recv_params.cseq,
            local_user=self.channel_list[2],
            local_ip=self.local_ip,
            local_port=self.local_port,
            server_user=send_params.server_user,
            server_ip=self.server_ip,
            server_port=self.server_port,
            tag=recv_params.tag,
            to_tag=recv_params.to_tag,
            method_type="request",
            message_type="ACK",
            subject="radio",
            allow=self.allow,
            supported=self.supported,
        )
        self._send_message(params)

    def bye(self, channel):
        """退出电台选中"""
        self._wait_response()
        # 切换电台或者退出非最后一个电台号
        if self.is_switch_radio or len(self.send_radio) + len(self.recv_radio) > 1:
            params = ReferParams(
                cseq=self._cseq_increment(),
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
            params = BaseMessageParams(
                cseq=self._cseq_increment(),
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
        self._send_message(params)

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

    def _check_timeout(self):
        """检查超时"""
        if len(self.send_history) > 0:
            current_time = time.time()
            params, message, send_time, retry_count = self.send_history[0]
            if current_time - send_time > self.retry_timeout:
                if retry_count < self.max_retries:
                    self.socket.sendto(message.encode(), (self.remote_ip, self.remote_port))
                    self.send_history[0] = (params, message, current_time, retry_count + 1)
                    print(f"消息 (CSeq: {params.cseq}) 超时未确认，进行第 {retry_count + 1} 次重传")
                else:
                    print(f"消息 (CSeq: {params.cseq}) 已达到最大重试次数 {self.max_retries}，放弃重传")

    def receive_message(self):
        """接收消息并处理"""
        while True:
            self._check_timeout()
            data, addr = self.socket.recvfrom(10240)  # 缓冲区大小
            message = data.decode('utf-8')
            self._handle_message(message)

    def _handle_message(self, message):
        """处理收到的SIP消息"""
        handle_status = False
        try:
            message_header, _, message_body = message.partition('\r\n\r\n')
            recv_params = parse_sip_message(message_header)
            if recv_params.status_code == 200:
                if recv_params.subject in ['vcu_phone', 'vcu_frequency', 'vcu_radio']:
                    handle_status = self._handle_btn_response(recv_params, message_body)
                else:
                    handle_status = self._handle_func_response(recv_params, message_body)
                if handle_status:
                    self.latest_cseq = self.send_history[0][0].cseq
                    self.send_history.popleft()
            else:
                print(f"收到非200响应: {recv_params.status_code}")
        except Exception as e:
            print(f"处理消息出错: {e}")

    def _handle_btn_response(self, recv_params, recv_message_body):
        """"处理按键响应"""
        # 当前待回复的报文
        send_params, _, _, _ = self.send_history[0]
        # 电话按键
        if send_params.subject == "vcu_phone" and recv_params.content_type == "application/phone_bt_info":
            info = TelBtnInfo.parse(recv_message_body)
        # 频率按键
        elif send_params.subject == "vcu_frequency" and recv_params.content_type == "application/frequency_bt_info":
            info = FreqBtnInfo.parse(recv_message_body)
            for info_t in info:
                self.frequency_list.append(str(info_t.frequency))
        # 电台按键
        elif send_params.subject == "vcu_radio" and recv_params.content_type == "application/radio_bt_info":
            info = RadioInfo.parse(recv_message_body)
            for info_t in info:
                radio = Radio(
                    freq=str(info_t.szFrequency.decode('utf-8')),
                    type=info_t.iRSType,
                    avail=info_t.iIsCan,
                )
                self.radio_dict[str(info_t.szCode.decode('utf-8'))] = radio
        else:
            return False

        return True if check_final_message(recv_params.cseq) else False

    def _handle_func_response(self, recv_params, recv_message_body):
        """处理功能响应"""
        # 当前待回复的报文
        send_params, _, _, _ = self.send_history[0]
        # 根据报文类型处理
        if send_params.cseq == recv_params.cseq:
            # 心跳报文
            if send_params.subject in ['vcu_logout', 'vcu_login']:
                return True
            # 注册报文
            elif send_params.subject == 'vcu_register':
                info = RoleInfo().parse(recv_message_body)
                self.channel_list = info.ChannelNum
                self.selected_role = info.szRoles[0].split(':')[0]
                self.status = 'online'
                return True
            # 电台操控报文
            elif send_params.subject == 'radio':
                return self._handle_radio_response(send_params, recv_params, recv_message_body)
        else:
            print(f'CSeq: {recv_params.cseq}')
            return False

    def _handle_radio_response(self, send_params, recv_params, recv_message_body):
        """处理电台操控响应"""
        port = send_params.server_user
        radio_func_type = 1
        if send_params.message_type == 'INVITE':
            radio_func_type = 1
            try:
                # 获取RTP端口
                match = re.search(r"m=audio (\d+)", recv_message_body)
                if match:
                    self.remote_port = int(match.group(1))
                    self.rtp_endpoint = RtpEndpoint(self.local_ip, self.local_rtp_port, self.remote_ip, self.remote_port)
                    self.rtp_endpoint.start()
                    self.ack(send_params, recv_params)
            except Exception as e:
                print(f"获取RTP端口错误 {e}")
        elif send_params.message_type == 'REFER' and send_params is None:
            radio_func_type = 1
        elif send_params.message_type == 'REFER' and send_params == 'BYE':
            radio_func_type = 0
        elif send_params.message_type == 'BYE':
            radio_func_type = 0
            self.rtp_endpoint.stop()
        else:
            return False

        if radio_func_type:
            if self.radio_dict[port].type == 0:
                self.send_radio.append(port)
            else:
                self.recv_radio.append(port)
        else:
            if port in self.send_radio:
                self.send_radio.remove(port)
            elif port in self.recv_radio:
                self.recv_radio.remove(port)

        return True
