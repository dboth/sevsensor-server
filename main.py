#!/usr/bin/python

from RPi import GPIO
import json, smbus2, bme280
from http.server import BaseHTTPRequestHandler, HTTPServer

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

def SevSensorServerHandler(sensor):
    class CustomHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
             super(CustomHandler, self).__init__(*args, **kwargs)
        
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps(sensor.getData())
            self.wfile.write(response.encode("utf-8"))
            print("got a request",response)

    return CustomHandler

class SevSensorServer:
    def __init__(self,port):
        self.initBME280()
        self.run(port)

    def initGPIO(self):
        try:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(11,GPIO.IN)
        except Exception as e:
            print("error establishing gpio",str(e))

    def initBME280(self):
        try:
            self.bme = {"bus": smbus2.SMBus(1), "address": 0x77, "cp":None}
            self.bme["cp"] = bme280.load_calibration_params(self.bme["bus"], self.bme["address"])
        except Exception as e:
            print("error establishing bme",str(e))

    def readBME(self):
        try:
            data = bme280.sample(self.bme["bus"],self.bme["address"],self.bme["cp"])
            return data
        except Exception as e:
            print("error while getting bme",str(e))
            return AttrDict({"temperature":None,"humidity": None, "pressure": None})

    def readTempSensor(self):
        with open('/sys/bus/w1/devices/28-02161f5a48ee/w1_slave', 'r') as f:
            lines = f.readlines()
        return lines

    def getTempSensor(self):
        try:
            lines = self.readTempSensor()
            while lines[0].strip()[-3:] != 'YES':
                time.sleep(0.2)
                lines = readTempSensor(sensorName)
            temperaturStr = lines[1].find('t=')
            if temperaturStr != -1 :
                tempData = lines[1][temperaturStr+2:]
                tempCelsius = float(tempData) / 1000.0
                return tempCelsius
        except Exception as e:
            print("error while getting tempsensor",str(e))
            return None


    def getData(self):
        bmeData = self.readBME()
        temperature = self.getTempSensor()
        if temperature is None:
            temperature = bmeData.temperature
        return {
            "airQualityIndex": None,
            "pm25": None,
            "voc": None,
            "temperature": temperature,
            "humidity": bmeData.humidity,
            "airPressure": bmeData.pressure,
            "carbonDioxideLevel": None,
            "carbonDioxideDetected": None
        }

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
