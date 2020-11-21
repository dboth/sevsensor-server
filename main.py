#!/usr/bin/python

from RPi import GPIO
from MHZ14Reader import MHZ14Reader
import qwiic_ccs811
import json, smbus2, bme280, math
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
        self.initCCS811()
        self.initMHZ14()
        self.run(port)

    def initGPIO(self):
        try:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(11,GPIO.IN)
        except Exception as e:
            print("error establishing gpio",str(e))

    def initMHZ14(self):
        try:
            self.mhz14 = MHZ14Reader("/dev/ttyAMA0")
            self.mhz14.zero_calibrationn()
        except Exception as e:
            print("error establishing mhz14",str(e))    

    def initCCS811(self):
        try:
            self.ccs811 = qwiic_ccs811.QwiicCcs811(address=0x5a)
            if self.ccs811.is_connected() == False:
                raise "Sensor not connected"
            self.ccs811.begin()
        except Exception as e:
            print("error establishing ccs811",str(e))

    def initBME280(self):
        try:
            self.bme = {"bus": smbus2.SMBus(1), "address": 0x77, "cp":None}
            self.bme["cp"] = bme280.load_calibration_params(self.bme["bus"], self.bme["address"])
        except Exception as e:
            print("error establishing bme",str(e))

    def readVOC(self, humidity, temperature):
        try:
            if humidity is not None and temperature is not None:
                self.ccs811.set_environmental_data(humidity,temperature)
            self.ccs811.read_algorithm_results()
            return self.ccs811.get_tvoc()
        except Exception as e:
            print("error while getting ccs811",str(e))
            return None

    def readCo2(self):
        try:
            status = self.mhz14.get_status()
            if status:
                return status["ppa"]
            raise "no value"
        except Exception as e:
            print("error while getting co2",str(e))
            return None

    def readBME(self):
        try:
            data = bme280.sample(self.bme["bus"],self.bme["address"],self.bme["cp"])
            return data
        except Exception as e:
            print("error while getting bme",str(e))
            return AttrDict({"temperature":None,"humidity": None, "pressure": None})

    def readTempSensor(self):
        with open('/sys/bus/w1/devices/28-0114639b25ff/w1_slave', 'r') as f:
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

    def fixHumidity(self, h, tn, t0):
        return h * math.exp(((17.27*t0)/(t0+273.3))-((17.27*t0)/(tn+273.3)))


    def getData(self):
        bmeData = self.readBME()

        humidity = bmeData.humidity
        pressure = bmeData.pressure
        bTemp = bmeData.temperature
        temperature = self.getTempSensor()
        tSource = "temperature-sensor"

        

        if temperature is None:
            temperature = bTemp
            tSource = "humidity-sensor"
        elif humidity is not None and bTemp is not None:
            humidity = self.fixHumidity(humidity, temperature, bTemp)

        voc = self.readVOC(humidity, temperature)

        co2 = self.readCo2()

        if co2 is not None and co2 > 1200:
            detected = 1
        else:
            detected = 0

        out = {
            "temperatureSource": tSource,
            "unfixedHumidity": bmeData.humidity,
            "bmeTemperature": bmeData.temperature,
            "airQualityIndex": 2,
            "pm25": None,
            "voc": voc,
            "temperature": temperature,
            "humidity": humidity,
            "airPressure": pressure,
            "carbonDioxideLevel": co2,
            "carbonDioxideDetected": detected
        }
        return {k: v for k, v in out.items() if v is not None}

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
