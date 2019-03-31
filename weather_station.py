#!/usr/bin/python
import argparse
import time

import smbus

from sensors.bme280 import get_temperature_pressure_humidity


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
      data_points = list(get_temperature_pressure_humidity(bus, device_address, verbose))

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
