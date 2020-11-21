#!/usr/bin/python

from RPi import GPIO
import json, smbus2, bme280
from http.server import BaseHTTPRequestHandler, HTTPServer


def SevSensorServerHandler(sensor):
    class CustomHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
             super(CustomHandler, self).__init__(*args, **kwargs)
             self.sensor = sensor
        
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.sensor.getData()))

    return CustomHandler

class SevSensorServer:
    def __init__(self,port):
        self.initBME280()
        self.run(port)

    def initGPIO(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(11,GPIO.IN)

    def initBME280(self):
        self.bme = {"bus": smbus2.SMBus(0), "address": 0x76, "cp":None}
        self.bme["cp"] = bme280.load_calibration_params(self.bme["bus"], self.bme["address"])

    def readBME(self):
        data = bme280.sample(self.bme["bus"],self.bme["address"],self.bme["cp"])
        return data

    def getData(self):
        return {"test":self.readBME()}

    def run(self,port):
        server_address = ("",port)
        HandlerClass = SevSensorServerHandler(self)
        httpd = HTTPServer(server_address,HandlerClass)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        #GPIO.cleanup()

if __name__ == '__main__':
    SevSensorServer(8080)