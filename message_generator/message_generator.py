import random
from uuid import uuid4
from data_classes.params_classes import BaseMessageParams, RegisterParams, InfoParams, ReferParams

class MessageGenerator:
    def __init__(self):
        self.cseq = 0
        self.branch_prefix = "z9hG4bK"
        self.call_id = str(uuid4())
        self.tag = str(random.randint(1000000000, 9999999999))
        self.user_agent = "Python SIP/2.0"
    
    def _generate_request_header(self, params: BaseMessageParams):
        """生成请求行"""
        return f"{params.message_type.upper()} sip:{params.server_user}@{params.server_ip}:{params.server_port} SIP/2.0"
    
    def _generate_response_header(self, params: BaseMessageParams):
        """生成状态行"""
        return f"SIP/2.0 {params.status_code} {params.reason_phrase}"

    def _generate_branch(self, params: BaseMessageParams):
        """生成符合RFC3261规范的branch ID"""
        if params.branch is None:
            return f"{self.branch_prefix}-{random.randint(1000000000, 9999999999)}"
        else:
            return params.branch
        
    def _generate_via_header(self, params: BaseMessageParams):
        """生成Via头"""
        return f"SIP/2.0/UDP {params.local_ip}:{params.local_port};branch={self._generate_branch(params)}"
    
    def _genearate_cseq_header(self, params: BaseMessageParams):
        """生成CSeq头"""
        if params.cseq is None:
            self.cseq += 1
            return f"{self.cseq} {params.message_type.upper()}"
        else:
            return f"{params.cseq} {params.message_type.upper()}"
            
    def _generate_call_id_header(self, params: BaseMessageParams):
        """"生成Call-ID头"""
        if params.call_id is None:
            return f"{str(random.randint(1000000000, 9999999999))}@{params.local_ip}"
        else:
            return params.call_id
        
    def _generate_tag(self, params: BaseMessageParams):
        """生成tag"""
        if params.tag is None:
            self.tag = str(random.randint(1000000000, 9999999999))
        else:
            self.tag = params.tag
    
    # 待修改 tag
    def _generate_from_header(self, params: BaseMessageParams):
        """生成From头"""
        self._generate_tag(params)
        if isinstance(params, RegisterParams) and params.password is not None:
            from_header = f"<sip:{params.local_user}:{params.password}@{params.server_ip}>;tag={self.tag}"
        else:
            from_header = f"<sip:{params.local_user}@{params.server_ip}>;tag={self.tag}"
        if isinstance(params, RegisterParams) and params.cwp is not None:
            from_header = from_header + f";cwp={params.cwp}"
        if isinstance(params, InfoParams) and params.roleid is not None:
            from_header = from_header + f";roleid={params.roleid}"
        return from_header
    
    def _generate_to_header(self, params: BaseMessageParams):
        """生成To头"""
        if (params.method_type == "response" or params.message_type == 'ACK'):
            return f"<sip:{params.server_user}@{params.server_ip}>;tag={self.tag}"
        else:
            return f"<sip:{params.server_user}@{params.server_ip}>"
    
    def _generate_contact_header(self, params: BaseMessageParams):
        """生成Contact头"""
        return f"<sip:{params.local_user}@{params.local_ip}:{params.local_port}>"
    
    def _generate_refer_to_header(self, params: ReferParams):
        """生成Refer-To头"""
        if params.method is not None:
            return f"<sip:{params.server_user}@{params.server_ip};method={params.method}>"
        else:
            return f"<sip:{params.server_user}@{params.server_ip}>"
    
    def _generate_refered_by_header(self, params: BaseMessageParams):
        """生成Refered-By头"""
        return f"<sip:{params.local_user}@{params.local_ip}>"
    
    def _generate_base_headers(self, params: BaseMessageParams):
        """生成基础头字段"""
        headers = [
            self._generate_request_header(params) if params.method_type == "request" else self._generate_response_header(params),
            f"Via: {self._generate_via_header(params)}",
            f"From: {self._generate_from_header(params)}",
            f"To: {self._generate_to_header(params)}",
            f"Call-ID: {self._generate_call_id_header(params)}",
            f"CSeq: {self._genearate_cseq_header(params)}",
            f"Max-Forwards: {params.max_forwards}",
        ]
        return headers
    
    def _gererate_headers(self, params: BaseMessageParams):
        """生成完整的SIP头"""
        headers = self._generate_base_headers(params)
        if params.subject is not None:
            headers.append(f"Subject: {params.subject}")
        if params.expires is not None:
            headers.append(f"Expires: {params.expires}")
        if params.contact is not None:
            headers.append(f"Contact: {self._generate_contact_header(params)}")
        if params.allow is not None:
            headers.append(f"Allow: {', '.join(params.allow)}")
        if params.supported is not None:
            headers.append(f"Supported: {', '.join(params.supported)}")
        if isinstance(params, ReferParams) and params.refer_to:
            headers.append(f"Refer-To: {self._generate_refer_to_header(params)}")
        if isinstance(params, ReferParams) and params.refered_by:
            headers.append(f"Refered-By: {self._generate_refered_by_header(params)}")
        return headers
    
    def _generate_content(self, params: BaseMessageParams):
        """生成消息内容"""
        content = params.content if params.content is not None else ""
        if content:
            return f"Content-Type: {params.content_type}\r\nContent-Length: {len(content)}\r\n\r\n{content}"
        else:
            return "Content-Length: 0\r\n\r\n"
        
    def generate_message(self, params: BaseMessageParams):
        """生成完整的SIP消息"""
        headers = self._gererate_headers(params)
        content = self._generate_content(params)
        return "\r\n".join(headers) + "\r\n" + content  
