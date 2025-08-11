from dataclasses import dataclass
from typing import Optional, List

@dataclass
class BaseMessageParams:
    method_type: str = "request"  
    message_type: str = "INFO"
    branch: Optional[str] = None
    call_id: Optional[str] = None
    cseq: Optional[int] = None
    tag: Optional[str] = None
    to_tag: Optional[str] = None
    local_user: str = None
    local_ip: str = None
    local_port: int = None
    remote_user: str = None
    remote_ip: str = None
    remote_port: int = None
    server_user: str = None
    server_ip: str = None
    server_port: int = None
    max_forwards: int = 70
    subject: Optional[str] = None
    expires: Optional[int] = None
    contact: Optional[str] = None
    allow: Optional[List[str]] = None
    supported: Optional[List[str]] = None
    content_type: Optional[str] = None
    content: Optional[str] = None
    status_code: Optional[int] = 200
    reason_phrase: Optional[str] = "OK"
    
@dataclass
class RegisterParams(BaseMessageParams):
    password: Optional[str] = None
    cwp: Optional[str] = None

@dataclass
class InfoParams(BaseMessageParams):
    roleid: Optional[str] = None

@dataclass
class ReferParams(BaseMessageParams):
    refer_to: Optional[str] = None
    refered_by: Optional[str] = None
    method: Optional[str] = None