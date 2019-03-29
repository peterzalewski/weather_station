import unittest

from mock import patch

from weather_station import read_bme280_data_points


class TestReadBME280DataPoints(unittest.TestCase):

  @patch('smbus.SMBus', auto_spec=True)
  def test_success(self, smbus):
    """Test the happy path with known data from a previous sample"""

    def read_data():
      # read_i2c_block_data(addr, 0x88, 24)
      yield [41, 111, 222, 102, 50, 0, 243, 140, 58, 214, 208, 11, 147, 34, 139, 255, 249, 255, 12, 48, 32, 209, 136, 19]

      # read_i2c_block_data(addr, 0xA1, 1)
      yield [75]

      # read_i2c_block_data(addr, 0xE1, 7)
      yield [77, 1, 0, 24, 45, 3, 30]

      # read_i2c_block_data(addr, REG_DATA, 8)
      yield [77, 82, 128, 130, 190, 0, 123, 250]

    # I find this more readable than directly assigning nested arrays to side_effect
    smbus.read_i2c_block_data.side_effect = list(read_data())

    temperature, pressure, humidity = read_bme280_data_points(smbus, 1)

    self.assertEqual(round(temperature, 2), 77.32)
    self.assertEqual(round(pressure, 2), 1022.19)
    self.assertEqual(round(humidity, 2), 31.94)


if __name__ == '__main__':
  unittest.main()
