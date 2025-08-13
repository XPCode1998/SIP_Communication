from typing import Union
import re
from dataclasses import fields
from data_classes.params_classes import BaseMessageParams, RegisterParams, InfoParams, ReferParams

def parse_sip_message(message: str) -> Union[BaseMessageParams, RegisterParams, InfoParams, ReferParams]:
    """
    解析SIP报文, 返回对应的参数对象
    
    Args:
        message: 完整的SIP报文字符串
        
    Returns:
        返回对应的参数对象(BaseMessageParams或其子类)
    """
    lines = message.split('\r\n')
    
    # 解析起始行
    first_line = lines[0]
    if first_line.startswith('SIP/2.0'):
        # 响应消息
        method_type = "response"
        status_code = int(first_line.split(' ')[1])
        reason_phrase = ' '.join(first_line.split(' ')[2:])
        message_type = None  # 需要从CSeq中获取
    else:
        # 请求消息
        method_type = "request"
        parts = first_line.split(' ')
        message_type = parts[0]
        sip_uri = parts[1]
        # 从SIP URI中提取用户、IP和端口
        uri_match = re.match(r'sip:(?P<user>[^@]+)@(?P<ip>[^:]+):?(?P<port>\d+)?', sip_uri)
        server_user = uri_match.group('user')
        server_ip = uri_match.group('ip')
        server_port = int(uri_match.group('port')) if uri_match.group('port') else 5060
    
    # 初始化参数字典
    params_dict = {
        'method_type': method_type,
        'message_type': message_type,
        'status_code': status_code if method_type == 'response' else None,
        'reason_phrase': reason_phrase if method_type == 'response' else None,
        'server_user': server_user if method_type == 'request' else None,
        'server_ip': server_ip if method_type == 'request' else None,
        'server_port': server_port if method_type == 'request' else None,
    }
    
    # 解析头部字段
    for line in lines[1:]:
        if not line.strip():
            break  # 空行表示头部结束
            
        if ':' in line:
            header_name, header_value = line.split(':', 1)
            header_name = header_name.strip().lower()
            header_value = header_value.strip()
            
            if header_name == 'via':
                # Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bK-123456
                via_parts = header_value.split(';')
                transport_ip_port = via_parts[0].strip()
                ip_port = transport_ip_port.split(' ')[1]
                ip, port = ip_port.split(':') if ':' in ip_port else (ip_port, '5060')
                params_dict['local_ip'] = ip
                params_dict['local_port'] = int(port)
                
                for part in via_parts[1:]:
                    if 'branch=' in part:
                        params_dict['branch'] = part.split('=')[1]
                        
            elif header_name == 'from':
                # From: <sip:1001@192.168.1.100>;tag=1234567890
                from_parts = header_value.split(';')
                uri_match = re.match(r'<sip:(?P<user>[^@]+)@(?P<ip>[^:>]+):?(?P<port>\d+)?>', from_parts[0])
                if uri_match:
                    params_dict['local_user'] = uri_match.group('user')
                    
                for part in from_parts[1:]:
                    if 'tag=' in part:
                        params_dict['tag'] = part.split('=')[1]
                    elif 'cwp=' in part:
                        params_dict['cwp'] = part.split('=')[1]
                    elif 'roleid=' in part:
                        params_dict['roleid'] = part.split('=')[1]
                    elif 'password=' in part:  # 非标准，仅示例
                        params_dict['password'] = part.split('=')[1]
                        
            elif header_name == 'to':
                # To: <sip:1000@192.168.1.1>;tag=9876543210
                to_parts = header_value.split(';')
                uri_match = re.match(r'<sip:(?P<user>[^@]+)@(?P<ip>[^:>]+):?(?P<port>\d+)?>', to_parts[0])
                if uri_match:
                    params_dict['remote_user'] = uri_match.group('user')
                    params_dict['remote_ip'] = uri_match.group('ip')
                    params_dict['remote_port'] = int(uri_match.group('port')) if uri_match.group('port') else 5060
                
                for part in to_parts[1:]:
                    if 'tag=' in part:
                        params_dict['to_tag'] = part.split('=')[1]
                        
            elif header_name == 'call-id':
                params_dict['call_id'] = header_value
                
            elif header_name == 'cseq':
                # CSeq: 1 REGISTER
                parts = header_value.split(' ')
                params_dict['cseq'] = int(parts[0])
                if method_type == 'response':
                    params_dict['message_type'] = parts[1].lower()
                    
            elif header_name == 'max-forwards':
                params_dict['max_forwards'] = int(header_value)
                
            elif header_name == 'subject':
                params_dict['subject'] = header_value
                
            elif header_name == 'expires':
                params_dict['expires'] = int(header_value)
                
            elif header_name == 'contact':
                params_dict['contact'] = header_value
                
            elif header_name == 'allow':
                params_dict['allow'] = [x.strip() for x in header_value.split(',')]
                
            elif header_name == 'supported':
                params_dict['supported'] = [x.strip() for x in header_value.split(',')]
                
            elif header_name == 'refer-to':
                params_dict['refer_to'] = header_value
                if ';method=' in header_value:
                    params_dict['method'] = header_value.split(';method=')[1].split('>')[0]
                    
            elif header_name == 'refered-by':
                params_dict['refered_by'] = header_value
                
            elif header_name == 'content-type':
                params_dict['content_type'] = header_value
                
    # 解析消息体
    empty_line_index = message.find('\r\n\r\n')
    if empty_line_index != -1 and len(message) > empty_line_index + 4:
        params_dict['content'] = message[empty_line_index + 4:]
    
    # 确定返回的参数类类型
    param_class = BaseMessageParams
    if 'password' in params_dict or 'cwp' in params_dict:
        param_class = RegisterParams
    elif 'roleid' in params_dict:
        param_class = InfoParams
    elif 'refer_to' in params_dict or 'refered_by' in params_dict:
        param_class = ReferParams
    
    # 创建参数对象
    param_fields = {f.name for f in fields(param_class)}
    filtered_params = {k: v for k, v in params_dict.items() if k in param_fields}
    
    return param_class(**filtered_params)