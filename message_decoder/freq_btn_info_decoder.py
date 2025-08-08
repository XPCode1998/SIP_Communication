import base64
import ctypes
from typing import List

class FreqBtnInfo(ctypes.Structure):
    _fields_ = [
        ("iPosition", ctypes.c_int),          # 所在按钮位置 (4字节)
        ("szFreqName", ctypes.c_char * 32),   # 按钮对应名称 (32字节)
        ("szFrequency", ctypes.c_char * 32),  # 电台频率 (32字节)
        ("iSaving", ctypes.c_int),            # 0：普通 1：救生 (4字节)
        ("iCanuse", ctypes.c_int)             # 是否使能 (0-否，1-是) (4字节)
    ]  # 总计 4 + 32 + 32 + 4 + 4 = 76 字节
    
    @classmethod
    def parse(cls, encoded_str: str) -> List['FreqBtnInfo']:
        """解析包含多组FreqBtnInfo的Base64字符串"""
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
    def saving_mode(self) -> str:
        """获取救生模式描述"""
        return "救生" if self.iSaving else "普通"
    
    @property
    def can_use(self) -> str:
        """获取使能状态描述"""
        return "可用" if self.iCanuse else "禁用"
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        return (
            f"位置: {self.iPosition}\n"
            f"名称: '{self.freq_name}'\n"
            f"频率: '{self.frequency}'\n"
            f"模式: {self.saving_mode}\n"
            f"状态: {self.can_use}"
        )


# 使用示例
if __name__ == "__main__":
    # 包含4组FREQBTNINFO结构的Base64字符串
    encoded_str = (
        "PQAAADEzMS42MTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMTMxLjYxMAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAD4AAAAxMzEuNjIwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADEz"
        "MS42MjAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/AAAAMTMxLjYzMAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAxMzEuNjMwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAQAAAADEzMS42NDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMTMxLjY0MAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAA=="
    )
    
    try:
        print(f"{' 开始解析多组频率数据 ':=^40}")
        freq_buttons = FreqBtnInfo.parse(encoded_str)
        
        for i, btn in enumerate(freq_buttons, 1):
            print(f"\n{' 频率组 '+str(i)+' ':-^30}")
            print(btn)
            # 也可以单独访问属性
            # print(f"频率值: {btn.frequency}")
        
        print(f"\n{' 解析完成 ':=^40}")
        print(f"共解析出 {len(freq_buttons)} 组频率数据")
        
    except Exception as e:
        print(f"解析错误: {e}")