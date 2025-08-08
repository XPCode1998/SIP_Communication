import base64
import ctypes
from typing import List
from dataclasses import dataclass
from typing import Optional, List

# 定义常量
CHANNEL_COUNT = 4
CHANNEL_LENGTH = 32
ROLES_LENGTH = 480
OTHER_CHOOSE_ROLE_LENGTH = 128


@dataclass
class Info:
    ChannelNum: Optional[List[str]] = None
    szRoles: Optional[List[str]] = None
    szOtherChooseRole: Optional[List[str]] = None


class RoleInfo:
    def __init__(self):
        self.ChannelNum = []
        self.szRoles = []
        self.szOtherChooseRole = []

    def parse(self, encoded_str):
        encoded_str = encoded_str.strip()

        try:
            decoded_data = base64.b64decode(encoded_str)
        except:
            raise ValueError(f"Base64解码失败")

        for i in range(CHANNEL_COUNT):
            self.ChannelNum.append(
                decoded_data[i * CHANNEL_LENGTH:(i + 1) * CHANNEL_LENGTH].decode('utf8').strip('\x00'))

        # 填充 szRoles 和 szOtherChooseRole（如果需要）
        roles_start = CHANNEL_LENGTH * CHANNEL_COUNT
        other_start = roles_start + ROLES_LENGTH
        roles_str = decoded_data[roles_start:other_start].decode('utf8').strip('\x00')
        self.szRoles = roles_str.split('+') if roles_str else []
        other_str = decoded_data[other_start:].decode('utf-8').strip('\x00')
        self.szOtherChooseRole = other_str.split('+') if other_str else []

        info = Info(
            ChannelNum=self.ChannelNum,
            szRoles=self.szRoles,
            szOtherChooseRole=self.szOtherChooseRole
        )

        return info


# 使用示例
if __name__ == "__main__":
    # 模拟包含2组RoleInfo的Base64数据
    encoded_str = "MzE2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzMTcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADMxOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMzE5AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAxMjpPUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="

    print(f"{' 开始解析多组角色数据 ':=^50}")
    role_info = RoleInfo().parse(encoded_str)

    print('ChannelNum: ', role_info.ChannelNum)
    print('szRoles: ', role_info.szRoles)
    print('szOtherChooseRole: ', role_info.szOtherChooseRole)