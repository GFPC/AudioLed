import time

import spidev
from libs.ws2812 import ws2812

LEDS_NUM = 90

spi = spidev.SpiDev()
spi.open(1,0)
ws2812.write2812(spi, [[10, 0, 0], [0, 10, 0], [0, 0, 10], [10, 10, 0]])

def ClearAll():
    buf = []
    for i in range(LEDS_NUM):
        buf.append([0, 0, 0])
    ws2812.write2812(spi, buf)

while True:
    buf = [[0, 0, 0] for i in range(LEDS_NUM)]
    for i in range(LEDS_NUM):
        buf[i] = [255, 255, 255]
        time.sleep(0.01)
        ws2812.write2812(spi, buf)
    time.sleep(1)
    ClearAll()
    time.sleep(1)