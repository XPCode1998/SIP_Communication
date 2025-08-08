import base64
import ctypes
from typing import List

class MyFunBtnInfo(ctypes.Structure):
    _fields_ = [
        ("iPosition", ctypes.c_int),       # 所在按钮位置 (4字节)
        ("szName", ctypes.c_char * 32),    # 按钮对应名称 (32字节)
        ("iType", ctypes.c_int)            # 功能键种类 (4字节)
    ]  # 总计 4 + 32 + 4 = 40字节
    
    @classmethod
    def parse(cls, encoded_str: str) -> List['MyFunBtnInfo']:
        """解析包含多组FunBtnInfo的Base64字符串"""
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
    def type_description(self) -> str:
        """获取功能键类型描述"""
        types = {
            0: "普通按钮",
            1: "快捷功能",
            2: "系统功能"
            # 可根据实际类型定义补充
        }
        return types.get(self.iType, f"未知类型({self.iType})")
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        return (
            f"按钮位置: {self.iPosition}\n"
            f"按钮名称: '{self.name}'\n"
            f"功能类型: {self.type_description}"
        )


# 使用示例
if __name__ == "__main__":
    # 模拟包含2组FunBtnInfo的Base64数据
    encoded_str = (
        "AQAAALGjwfQAb2xkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKAAAAAIAAAC69L3Q16rSxgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACkAAAADAAAAtee7sNeqvdMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAqAAAABAAAALvh0ukAb25mAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKwAAAAUAAAC+stL0AHV0ZQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAAAAAGAAAAu9i3xQBsYXliYWNrAAAAAAAAAAAAAAAAAAAAAAAAAAAxAAAABwAAAMe/svAAcmlvAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALAAAAA=="
    )
    
    try:
        print(f"{' 开始解析功能按钮数据 ':=^50}")
        btn_infos = MyFunBtnInfo.parse(encoded_str)
        
        for i, btn in enumerate(btn_infos, 1):
            print(f"\n{' 功能按钮 '+str(i)+' ':-^40}")
            print(btn)
            # 也可以单独访问属性
            # print(f"按钮名称: {btn.name}")
        
        print(f"\n{' 解析完成 ':=^50}")
        print(f"共解析出 {len(btn_infos)} 组功能按钮数据")
        
    except Exception as e:
        print(f"解析错误: {e}")