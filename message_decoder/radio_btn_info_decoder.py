import base64
import ctypes
from typing import List

class RadioInfo(ctypes.Structure):
    _fields_ = [
        ("iPosition", ctypes.c_int),          # 所在按钮位置 (4字节)
        ("szFreqName", ctypes.c_char * 32),   # 按钮对应名称 (32字节)
        ("szFrequency", ctypes.c_char * 32),  # 电台频率 (32字节)
        ("szCode", ctypes.c_char * 12),       # 电台发内码组号 (12字节)
        ("szRadioName", ctypes.c_char * 32),  # 电台对应名称 (32字节)
        ("iRSType", ctypes.c_int),            # 收发类型 (4字节)
        ("iIsCan", ctypes.c_int)              # 是否可用 (4字节)
    ]  # 总计 4 + 32 + 32 + 12 + 32 + 4 + 4 = 120字节
    
    @classmethod
    def parse(cls, encoded_str: str) -> List['RadioInfo']:
        """解析包含多组RadioInfo的Base64字符串"""
        encoded_str = encoded_str.strip()
        
        try:
            decoded_data = base64.b64decode(encoded_str)
        except Exception as e:
            raise ValueError(f"Base64解码失败: {e}")
        
        # 计算每组数据大小和组数
        entry_size = ctypes.sizeof(cls)
        if len(decoded_data) % entry_size != 0:
            raise ValueError(f"数据长度{len(decoded_data)}不是{entry_size}的整数倍")
        
        entry_count = len(decoded_data) // entry_size
        results = []
        
        for i in range(entry_count):
            # 创建新实例并复制数据
            entry = cls()
            start = i * entry_size
            end = start + entry_size
            ctypes.memmove(ctypes.addressof(entry), decoded_data[start:end], entry_size)
            results.append(entry)
            
        return results
    
    @property
    def freq_name(self) -> str:
        """获取频率名称"""
        return self.szFreqName.decode('ascii').strip('\x00')
    
    @property
    def frequency(self) -> str:
        """获取频率值"""
        return self.szFrequency.decode('ascii').strip('\x00')
    
    @property
    def code(self) -> str:
        """获取内码组号"""
        return self.szCode.decode('ascii').strip('\x00')
    
    @property
    def radio_name(self) -> str:
        """获取电台名称"""
        return self.szRadioName.decode('ascii').strip('\x00')
    
    @property
    def rs_type(self) -> str:
        """获取收发类型描述"""
        return "发" if self.iRSType else "收"
    
    @property
    def is_available(self) -> str:
        """获取可用状态描述"""
        return "可用" if self.iIsCan else "不可用"
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        return (
            f"位置: {self.iPosition}\n"
            f"频率名称: '{self.freq_name}'\n"
            f"频率值: '{self.frequency}'\n"
            f"内码组号: '{self.code}'\n"
            f"电台名称: '{self.radio_name}'\n"
            f"收发类型: {self.rs_type}\n"
            f"可用状态: {self.is_available}"
        )


# 使用示例
if __name__ == "__main__":
    # 模拟包含2组RadioInfo的Base64数据
    encoded_str = (
        "CQAAAAAAAABWSEYgQ2hhbm5lbCAxICAgICAgICAgICAxNDUuNTAwICAgICAgICAg"
        "ICAgICAwMDEyICAgICAgICAgICBSYWRpbyBWSEYgMSAgICAgICAgICAgMQAAAAAA"
        "AAEAAAAAAAAA"
        "DAAAAAAAAABWSEYgQ2hhbm5lbCAyICAgICAgICAgICAxNDYuNTAwICAgICAgICAg"
        "ICAgICAwMDEzICAgICAgICAgICBSYWRpbyBWSEYgMiAgICAgICAgICAgMQAAAAAA"
        "AAEAAAAAAAAA"
    )
    
    try:
        print(f"{' 开始解析多组电台数据 ':=^50}")
        radio_infos = RadioInfo.parse(encoded_str)
        
        for i, radio in enumerate(radio_infos, 1):
            print(f"\n{' 电台组 '+str(i)+' ':-^40}")
            print(radio)
            # 也可以单独访问属性
            # print(f"频率值: {radio.frequency}")
        
        print(f"\n{' 解析完成 ':=^50}")
        print(f"共解析出 {len(radio_infos)} 组电台数据")
        
    except Exception as e:
        print(f"解析错误: {e}")