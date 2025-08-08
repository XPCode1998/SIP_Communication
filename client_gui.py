from sip.sip_client import SIPClient
import json
import threading
import time
from tkinter import Tk, Label, Button, Entry, StringVar, messagebox, Frame, Text, Scrollbar


class SIPClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("SIP客户端控制面板")

        # 加载配置文件
        with open('./config/comm_config.json', 'r') as file:
            self.config = json.load(file)

        # 初始化SIP客户端
        self.sip_client = SIPClient(
            user='bxp',
            local_ip=self.config['client']['ip'],
            local_port=self.config['client']['port'],
            remote_ip=self.config['server']['ip'],
            remote_port=self.config['server']['port'],
            local_rtp_port=self.config['client']['rtp_port'],
            remote_rtp_port=self.config['server']['rtp_port'],
        )

        # 启动客户端的消息接收线程
        self.client_thread = threading.Thread(target=self.sip_client.receive_message)
        self.client_thread.daemon = True
        self.client_thread.start()

        # 初始化UI
        self.create_widgets()

        # 自动注册
        self.sip_client.keep_alive()
        self.sip_client.register()

    def create_widgets(self):
        # 主框架
        main_frame = Frame(self.master)
        main_frame.pack(padx=10, pady=10)

        # 控制按钮区域
        control_frame = Frame(main_frame)
        control_frame.pack(pady=5)

        Button(control_frame, text="获取频率按钮", command=self.get_frequency).pack(side='left', padx=5)
        Button(control_frame, text="获取电台按钮", command=self.get_radio).pack(side='left', padx=5)

        # 电台选择区域
        radio_frame = Frame(main_frame)
        radio_frame.pack(pady=5)

        Label(radio_frame, text="电台ID:").pack(side='left')
        self.radio_id_var = StringVar()
        Entry(radio_frame, textvariable=self.radio_id_var, width=10).pack(side='left', padx=5)
        Button(radio_frame, text="选择电台", command=self.select_radio).pack(side='left', padx=5)

        # 结束通话区域
        bye_frame = Frame(main_frame)
        bye_frame.pack(pady=5)

        Label(bye_frame, text="结束通话ID:").pack(side='left')
        self.bye_id_var = StringVar()
        Entry(bye_frame, textvariable=self.bye_id_var, width=10).pack(side='left', padx=5)
        Button(bye_frame, text="结束通话", command=self.bye_call).pack(side='left', padx=5)

        # 日志区域
        log_frame = Frame(main_frame)
        log_frame.pack(pady=5)

        Label(log_frame, text="操作日志:").pack(anchor='w')

        self.log_text = Text(log_frame, height=10, width=50)
        scrollbar = Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 退出按钮
        Button(main_frame, text="退出", command=self.on_closing).pack(pady=5)

    def log_message(self, message):
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')

    def get_frequency(self):
        try:
            self.log_message("正在获取频率按钮...")
            self.sip_client.get_frequency_btn()
            self.log_message("获取频率按钮请求已发送")
        except Exception as e:
            self.log_message(f"获取频率按钮出错: {str(e)}")

    def get_radio(self):
        try:
            self.log_message("正在获取电台按钮...")
            self.sip_client.get_radio_btn()
            self.log_message("获取电台按钮请求已发送")
        except Exception as e:
            self.log_message(f"获取电台按钮出错: {str(e)}")

    def select_radio(self):
        radio_id = self.radio_id_var.get()
        if not radio_id:
            messagebox.showwarning("警告", "请输入电台ID")
            return

        try:
            self.log_message(f"正在选择电台 {radio_id}...")
            self.sip_client.select_radio(radio_id)
            self.log_message(f"选择电台 {radio_id} 请求已发送")
        except Exception as e:
            self.log_message(f"选择电台出错: {str(e)}")

    def bye_call(self):
        bye_id = self.bye_id_var.get()
        if not bye_id:
            messagebox.showwarning("警告", "请输入要结束的通话ID")
            return

        try:
            self.log_message(f"正在结束通话 {bye_id}...")
            self.sip_client.bye(bye_id)
            self.log_message(f"结束通话 {bye_id} 请求已发送")
        except Exception as e:
            self.log_message(f"结束通话出错: {str(e)}")

    def on_closing(self):
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.master.destroy()


if __name__ == '__main__':
    root = Tk()
    gui = SIPClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)
    root.mainloop()