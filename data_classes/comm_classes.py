from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Radio:
    freq: Optional[str] = None
    type: Optional[int] = 0
    avail: Optional[int] = 0