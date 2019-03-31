from ctypes import c_short


def get_short(data, index):
  """Return two bytes from data as a signed 16-bit value"""
  return c_short((data[index+1] << 8) + data[index]).value

def get_unsigned_short(data, index):
  """Return two bytes from data as an unsigned 16-bit value"""
  return (data[index+1] << 8) + data[index]

def get_char(data, index):
  """Return one byte from data as a signed char"""
  result = data[index]
  if result > 127:
    result -= 256
  return result

def get_unsigned_char(data, index):
  """Return one byte from data as an unsigned char"""
  result = data[index] & 0xFF
  return result
