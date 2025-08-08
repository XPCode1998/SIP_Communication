import pyaudio
import socket
import time
import audioop
import random
import threading
from collections import deque


class RtpEndpoint:
    def __init__(self, local_ip='127.0.0.1', local_port=16386,
                 remote_ip='127.0.0.1', remote_port=16387):
        """RTP端点类，实现双向音频通信

        Args:
            local_ip: 本地监听IP地址
            local_port: 本地监听端口
            remote_ip: 远程目标IP地址
            remote_port: 远程目标端口
        """
        # RTP协议配置常量
        self.RTP_VERSION = 2
        self.RTP_PAYLOAD_TYPE = 8  # G.711 PCMA编码
        self.RTP_SSRC = random.randint(0, 0xFFFFFFFF)  # 同步源标识符

        # 网络配置
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port

        # 音频参数配置
        self.sample_rate = 8000  # 采样率(Hz)
        self.channels = 1  # 声道数
        self.frame_duration = 20  # 帧时长(ms)
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
        self.voice_threshold = 100  # 语音活动检测阈值
        self.sample_width = 2

        # 初始化音频设备
        self.audio = pyaudio.PyAudio()
        # 音频输入流(麦克风)
        self.input_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.audio.get_default_input_device_info()['index'],
            frames_per_buffer=self.frame_size
        )
        # 音频输出流(扬声器)
        self.output_stream = self.audio.open(
            format=self.audio.get_format_from_width(self.sample_width),
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=self.frame_size
        )

        # 初始化网络套接字
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.local_ip, self.local_port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)

        # RTP序列控制
        self.sequence_number = 0
        self.timestamp = 0

        # 抖动缓冲区
        self.buffer_size = int(self.sample_rate * 0.05 / self.frame_size)
        self.jitter_buffer = deque(maxlen=self.buffer_size)

        # 线程控制标志
        self.is_running = False

    def create_rtp_header(self, marker_bit):
        """创建RTP协议头部

        Args:
            marker_bit: 标记位，1表示有语音活动

        Returns:
            bytes: 12字节的RTP头部数据
        """
        # 版本号(2bit)+填充位(1bit)+扩展位(1bit)+CSRC计数(4bit)
        version_p_pt = (self.RTP_VERSION << 6) | (0 << 5) | (self.RTP_PAYLOAD_TYPE & 0x7F)
        marker = (marker_bit << 7)

        return bytes([
            version_p_pt,  # 第一个字节
            marker | (self.RTP_PAYLOAD_TYPE & 0x7F),  # 第二个字节
            (self.sequence_number >> 8) & 0xFF,  # 序列号高8位
            self.sequence_number & 0xFF,  # 序列号低8位
            (self.timestamp >> 24) & 0xFF,  # 时间戳最高字节
            (self.timestamp >> 16) & 0xFF,
            (self.timestamp >> 8) & 0xFF,
            self.timestamp & 0xFF,  # 时间戳最低字节
            (self.RTP_SSRC >> 24) & 0xFF,  # SSRC标识符最高字节
            (self.RTP_SSRC >> 16) & 0xFF,
            (self.RTP_SSRC >> 8) & 0xFF,
            self.RTP_SSRC & 0xFF  # SSRC标识符最低字节
        ])

    def send_audio(self):
        """音频发送线程函数，每20ms发送一帧"""
        next_send_time = time.perf_counter() + (self.frame_duration / 1000)

        while self.is_running:
            print('尝试读取音频数据...')
            # 从麦克风读取音频数据
            pcm_data = self.input_stream.read(
                self.frame_size,
                exception_on_overflow=False
            )

            # 计算RMS值检测语音活动
            rms_value = audioop.rms(pcm_data, 2)
            has_voice = 1 if rms_value > self.voice_threshold else 0

            print(f'has_voice: {has_voice}')

            # PCM转G.711 A-law
            alaw_data = audioop.lin2alaw(pcm_data, 2)

            # 构造RTP数据包
            header = self.create_rtp_header(has_voice)
            packet = header + alaw_data

            # 发送到对端
            self.socket.sendto(packet, (self.remote_ip, self.remote_port))

            # 更新序列号和时间戳
            self.sequence_number = (self.sequence_number + 1) & 0xFFFF
            self.timestamp = (self.timestamp + self.frame_size) & 0xFFFFFFFF

            # 精确控制发送间隔
            current_time = time.perf_counter()
            sleep_duration = next_send_time - current_time
            if sleep_duration > 0:
                time.sleep(sleep_duration)
            next_send_time += (self.frame_duration / 1000)

    def receive_audio(self):
        """音频接收处理函数"""
        while self.is_running:
            # 接收RTP数据包
            packet, _ = self.socket.recvfrom(2048)

            # 验证数据包长度
            if len(packet) < 12 + self.frame_size:
                continue

            # 解析RTP头部
            header = packet[:12]
            version = (header[0] >> 6) & 0x03
            payload_type = header[1] & 0x7F
            marker = (header[1] >> 7) & 0x01

            # 验证协议版本和负载类型
            if version != self.RTP_VERSION or payload_type != self.RTP_PAYLOAD_TYPE:
                continue

            # 提取并转换音频数据
            alaw_data = packet[12:12 + self.frame_size]
            pcm_data = audioop.alaw2lin(alaw_data, 2)


            # 加入抖动缓冲区
            self.jitter_buffer.append((pcm_data, marker))


            # 从缓冲区取出数据播放
            if len(self.jitter_buffer) >= self.buffer_size:
                audio_frame, marker_status = self.jitter_buffer.popleft()
                self.output_stream.write(audio_frame)
                # print(f"收到数据包 - 标记位: {marker_status}", end='\r')

    def start(self):
        """启动RTP端点"""
        self.is_running = True
        # 启动发送线程
        sender_thread = threading.Thread(target=self.send_audio)
        sender_thread.daemon = True
        sender_thread.start()

        receiver_thread = threading.Thread(target=self.receive_audio)
        receiver_thread.daemon = True
        receiver_thread.start()

        # # 在主线程运行接收函数
        # try:
        #     self.receive_audio()
        # except KeyboardInterrupt:
        #     self.stop()

    def stop(self):
        """停止并释放资源"""
        self.is_running = False
        self.input_stream.stop_stream()
        self.input_stream.close()
        self.output_stream.stop_stream()
        self.output_stream.close()
        self.audio.terminate()
        self.socket.close()
        print("\nRTP端点已停止")


if __name__ == "__main__":
    import sys

    # 根据命令行参数决定运行模式
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # 服务端配置
        endpoint = RtpEndpoint(
            local_ip='127.0.0.1',
            local_port=16386,
            remote_ip='127.0.0.1',
            remote_port=16387
        )
        print("启动RTP服务端 (发送端口:16387, 接收端口:16386)")
    else:
        # 客户端配置
        endpoint = RtpEndpoint(
            local_ip='127.0.0.1',
            local_port=16387,
            remote_ip='127.0.0.1',
            remote_port=16386
        )
        print("启动RTP客户端 (发送端口:16386, 接收端口:16387)")

    # 启动端点
    endpoint.start()