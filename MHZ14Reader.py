from typing import Optional
import serial

defaultPort = '/dev/ttyUSB0'

class MHZ14Reader:
    """
    Simple sensor communication class.
    No calibration method provided to avoid accidental sensor bricking (calibrating to wrong levels)
    """

    _requestSequence = bytes([0xff, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])
    _calibrateZeroSequence = bytes([0xff, 0x01, 0x87, 0x00, 0x00, 0x00, 0x00, 0x00, 0x78])
    _calibrateSpansequence = bytes([0xff, 0x01, 0x88, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    port: str
    link: Optional[serial.Serial] = None

    def __init__(self, port: str, open_connection: bool = True):
        """
        :param string port: path to tty
        :param bool open_connection: should port be opened immediately
        """
        self.port = port
        """Connection with sensor"""
        if open_connection:
            self.connect()

    def connect(self):
        """
        Open tty connection to sensor
        """
        if self.link is not None:
            self.disconnect()
        self.link = serial.Serial(self.port, 9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                  stopbits=serial.STOPBITS_ONE, dsrdtr=True, timeout=5, interCharTimeout=0.1)

    def disconnect(self):
        """
        Terminate sensor connection
        """
        if self.link:
            self.link.close()
        self.link = None

    def get_status(self) -> Optional[dict]:
        """
        Read data from sensor
        :return {ppa, t, checksum}|None:
        """
        self.link.write(self._requestSequence)
        response = self.link.read(9)
        if len(response) == 9:
            return {
                "ppa": response[2] * 0xff + response[3],
                "t": response[4],
                "checksum": self._validate_checksum(response),
            }
        return None

    def _checksum(self, msg: bytes) -> int:
        """
        Calculate message checksum
        """
        return 0xff - (sum(msg[i] for i in range(1, 7)) & 0xff) + 1  # formula from datasheet

    def _validate_checksum(self, msg: bytes) -> bool:
        """
        Check if message contains correct checksum
        """
        return self._checksum(msg) == msg[8]

    def zero_calibrationn(self):
        """
        Trigger zero calibration (0PPM for Z14, 400 PPM for Z19)
        """
        self.link.write(self._calibrateZeroSequence)

    def span_calibration(self, value: int):
        """
        trigger span point calibration
        :param value:
        """
        msg = bytearray(self._calibrateSpansequence)
        if not (800 < value < 2200):
            raise AssertionError("datasheet expects to use values between 1000 and 2000 ppm")
        msg[3] = (value & 0xff00) >> 8
        msg[4] = value & 0xff
        self.link.write(msg)