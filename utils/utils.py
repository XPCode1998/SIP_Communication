
#
def check_final_message(num):
    high_byte = (num & 0xff00) >> 8
    low_byte = num & 0xff
    return high_byte == low_byte
