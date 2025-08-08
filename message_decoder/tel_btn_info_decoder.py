import base64
import ctypes
from typing import List

class TelBtnInfo(ctypes.Structure):
    _fields_ = [
        ("iPosition", ctypes.c_int),               # 所在按钮位置 (4字节)
        ("szName", ctypes.c_char * 32),            # 按钮对应名称 (32字节)
        ("szTelNumber", ctypes.c_char * 32),       # 按钮对应的号码 (32字节)
        ("iDial", ctypes.c_int),                   # 是否需要弹出拨号盘 (4字节)
        ("iCanuse", ctypes.c_int),                 # 是否使能 (4字节)
        ("iType", ctypes.c_int),                   # 号码类型 (4字节)
        ("iStatus", ctypes.c_uint),                # 状态 (4字节)
        ("dep_id", ctypes.c_int)                   # 部门ID (4字节)
    ]  # 总计 4 + 32 + 32 + 4 + 4 + 4 + 4 + 4 = 88字节
    
    @classmethod
    def parse(cls, encoded_str: str) -> List['TelBtnInfo']:
        """解析包含多组TelBtnInfo的Base64字符串"""
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
    def name(self) -> str:
        """获取按钮名称"""
        return self.szName.decode('ascii').strip('\x00')
    
    @property
    def tel_number(self) -> str:
        """获取电话号码"""
        return self.szTelNumber.decode('ascii').strip('\x00')
    
    @property
    def type_description(self) -> str:
        """获取类型描述"""
        types = {
            1: "模拟电话",
            2: "中继",
            3: "速拨",
            4: "组拨号",
            5: "IP电话",
            6: "磁石电话",
            7: "席位电话",
            8: "中继线路号"
        }
        return types.get(self.iType, f"未知类型({self.iType})")
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        return (
            f"位置: {self.iPosition}\n"
            f"名称: '{self.name}'\n"
            f"号码: '{self.tel_number}'\n"
            f"拨号盘: {'是' if self.iDial else '否'}\n"
            f"使能: {'是' if self.iCanuse else '否'}\n"
            f"类型: {self.type_description}\n"
            f"状态: 0x{self.iStatus:08X}\n"
            f"部门ID: {self.dep_id}"
        )


# 使用示例
if __name__ == "__main__":
    # 模拟包含2组TelBtnInfo的Base64数据
    encoded_str = (
        "AQAAAAAAAABUZXN0IEJ1dHRvbiAgICAgICAgICAgICAxMjM0NTY3ODkwICAgICAgICAg"
        "ICAgICAgICAgICAxAAAAAAAAADIAAAAAAAAANAAAAAAAAAA="
        "AgAAAAAAAABUZXN0IEJ1dHRvbiAyICAgICAgICAgICAyMjMzNDQ1NTY2ICAgICAgICAg"
        "ICAgICAgICAgICAyAAAAAAAAADMAAAAAAAAANQAAAAAAAAA="
    )
    
    try:
        print(f"{' 开始解析多组电话按键数据 ':=^50}")
        buttons = TelBtnInfo.parse(encoded_str)
        
        for i, btn in enumerate(buttons, 1):
            print(f"\n{' 电话按键组 '+str(i)+' ':-^40}")
            print(btn)
            # 也可以单独访问属性
            # print(f"号码类型: {btn.type_description}")
        
        print(f"\n{' 解析完成 ':=^50}")
        print(f"共解析出 {len(buttons)} 组数据")
        
    except Exception as e:
        print(f"解析错误: {e}")