#!/usr/bin/python
import argparse
import time
from ctypes import c_short

import smbus


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

def read_bme280_data_points(bus, addr, verbose=False):
  # Original code:
  #
  # Author : Matt Hawkins
  # Date   : 21/01/2018
  # https://www.raspberrypi-spy.co.uk/

  # Register Addresses
  REG_DATA = 0xF7
  REG_CONTROL = 0xF4
  REG_CONTROL_HUM = 0xF2

  # Oversample setting - page 27
  OVERSAMPLE_TEMP = 2
  OVERSAMPLE_PRES = 2
  MODE = 1

  # Oversample setting for humidity register - page 26
  OVERSAMPLE_HUM = 2

  bus.write_byte_data(addr, REG_CONTROL_HUM, OVERSAMPLE_HUM)

  control = OVERSAMPLE_TEMP<<5 | OVERSAMPLE_PRES<<2 | MODE
  bus.write_byte_data(addr, REG_CONTROL, control)

  # Read blocks of calibration data from EEPROM
  # See Page 22 data sheet
  cal1 = bus.read_i2c_block_data(addr, 0x88, 24)
  cal2 = bus.read_i2c_block_data(addr, 0xA1, 1)
  cal3 = bus.read_i2c_block_data(addr, 0xE1, 7)

  if verbose:
    print "Temperature calibration data: {}".format(cal1)
    print "Pressure calibration data: {}".format(cal2)
    print "Humidity calibration data: {}".format(cal3)

  # Convert byte data to word values
  dig_t1 = get_unsigned_short(cal1, 0)
  dig_t2 = get_short(cal1, 2)
  dig_t3 = get_short(cal1, 4)

  dig_p1 = get_unsigned_short(cal1, 6)
  dig_p2 = get_short(cal1, 8)
  dig_p3 = get_short(cal1, 10)
  dig_p4 = get_short(cal1, 12)
  dig_p5 = get_short(cal1, 14)
  dig_p6 = get_short(cal1, 16)
  dig_p7 = get_short(cal1, 18)
  dig_p8 = get_short(cal1, 20)
  dig_p9 = get_short(cal1, 22)

  dig_h1 = get_unsigned_char(cal2, 0)
  dig_h2 = get_short(cal3, 0)
  dig_h3 = get_unsigned_char(cal3, 2)

  dig_h4 = get_char(cal3, 3)
  dig_h4 = (dig_h4 << 24) >> 20
  dig_h4 = dig_h4 | (get_char(cal3, 4) & 0x0F)

  dig_h5 = get_char(cal3, 5)
  dig_h5 = (dig_h5 << 24) >> 20
  dig_h5 = dig_h5 | (get_unsigned_char(cal3, 4) >> 4 & 0x0F)

  dig_h6 = get_char(cal3, 6)

  # Wait in ms (Datasheet Appendix B: Measurement time and current calculation)
  wait_time = 1.25 + (2.3 * OVERSAMPLE_TEMP) + ((2.3 * OVERSAMPLE_PRES) + 0.575) + ((2.3 * OVERSAMPLE_HUM)+0.575)
  time.sleep(wait_time/1000)  # Wait the required time

  # Read temperature/pressure/humidity
  data = bus.read_i2c_block_data(addr, REG_DATA, 8)
  pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
  temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
  hum_raw = (data[6] << 8) | data[7]

  #Refine temperature
  var1 = ((((temp_raw>>3)-(dig_t1<<1)))*(dig_t2)) >> 11
  var2 = (((((temp_raw>>4) - (dig_t1)) * ((temp_raw>>4) - (dig_t1))) >> 12) * (dig_t3)) >> 14
  t_fine = var1+var2
  temperature = float(((t_fine * 5) + 128) >> 8)

  # Refine pressure and adjust for temperature
  var1 = t_fine / 2.0 - 64000.0
  var2 = var1 * var1 * dig_p6 / 32768.0
  var2 = var2 + var1 * dig_p5 * 2.0
  var2 = var2 / 4.0 + dig_p4 * 65536.0
  var1 = (dig_p3 * var1 * var1 / 524288.0 + dig_p2 * var1) / 524288.0
  var1 = (1.0 + var1 / 32768.0) * dig_p1
  if var1 == 0:
    pressure = 0
  else:
    pressure = 1048576.0 - pres_raw
    pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
    var1 = dig_p9 * pressure * pressure / 2147483648.0
    var2 = pressure * dig_p8 / 32768.0
    pressure = pressure + (var1 + var2 + dig_p7) / 16.0

  # Refine humidity
  humidity = t_fine - 76800.0
  humidity = (hum_raw - (dig_h4 * 64.0 + dig_h5 / 16384.0 * humidity)) * \
    (dig_h2 / 65536.0 * (1.0 + dig_h6 / 67108864.0 * humidity * (1.0 + dig_h3 / 67108864.0 * humidity)))
  humidity = humidity * (1.0 - dig_h1 * humidity / 524288.0)
  if humidity > 100:
    humidity = 100
  elif humidity < 0:
    humidity = 0

  fahrenheit = (temperature/100.0 * 9) / 5 + 32
  return fahrenheit, pressure / 100.0, humidity

def spin_and_log_data_points(device_address, interval_sec=5, verbose=False):
  """
  Print all current data points from the given BME280 sensor at a regular interval.

  Args:
    device_address (int): I2C address of the BME280 sensor to poll
    interval_sec (int): Number of seconds to wait between polls. Defaults to 5.
  """

  try:
    bus = smbus.SMBus(1)
  except IOError as ex:
    if ex.errno == 2:
      print "Error: Most likely bus does not exist"
    elif ex.errno == 13:
      print "Error: Mosty likely insufficient permission to access I2C bus"
    raise

  try:
    while True:
      data_points = list(read_bme280_data_points(bus, device_address, verbose))

      #  2019-03-28 TODO: pretty printing
      print ",".join([
        str(round(data_point, 2))
        for data_point in data_points
      ])

      time.sleep(interval_sec)
  except IOError as ex:
    if ex.errno == 121:
      print "Error: Most likely wrong device address for BME280 sensor"
    raise
  except KeyboardInterrupt:
    print "Interrupted - Stopped logging"

if __name__ == "__main__":
  argument_parser = argparse.ArgumentParser()
  argument_parser.add_argument(
    "-d",
    "--device_address",
    type=int,
    default=0x77,
    help="the I2C address of the BME280 sensor to poll")
  argument_parser.add_argument(
    "-i",
    "--interval_sec",
    type=int,
    default=5,
    help="the number of seconds to wait between polls. Defaults to 5")
  argument_parser.add_argument("-v", "--verbose", action="store_true")
  arguments = argument_parser.parse_args()

  spin_and_log_data_points(**dict(arguments._get_kwargs()))
