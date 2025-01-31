import numpy
import signal, sys, time, math
import spidev, ws2812, colorsys

PIXELS = 150
BRIGHTNESS = 255
VELOCITY = 10
SPI_DEVICE = 0

spi = spidev.SpiDev()
spi.open(SPI_DEVICE, 0)

def signal_handler(sig, frame):
  print('You pressed Ctrl+C!')
  data = numpy.zeros((PIXELS, 3), dtype=numpy.uint8)
  ws2812.write2812(spi, data)
  sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

gamma_table = (0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,4,4,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7,8,8,8,9,9,9,10,10,10,11,11,11,12,12,13,13,13,14,14,15,15,16,16,17,17,18,18,19,19,20,20,21,21,22,22,23,24,24,25,25,26,27,27,28,29,29,30,31,32,32,33,34,35,35,36,37,38,39,39,40,41,42,43,44,45,46,47,48,49,50,50,51,52,54,55,56,57,58,59,60,61,62,63,64,66,67,68,69,70,72,73,74,75,77,78,79,81,82,83,85,86,87,89,90,92,93,95,96,98,99,101,102,104,105,107,109,110,112,114,115,117,119,120,122,124,126,127,129,131,133,135,137,138,140,142,144,146,148,150,152,154,156,158,160,162,164,167,169,171,173,175,177,180,182,184,186,189,191,193,196,198,200,203,205,208,210,213,215,218,220,223,225,228,231,233,236,239,241,244,247,249,252,255)

def gamma(c):
  r = max(min(int(c[0]), 255), 0)
  g = max(min(int(c[1]), 255), 0)
  b = max(min(int(c[2]), 255), 0)
  return (r, g, b)

data = numpy.zeros((PIXELS, 3), dtype=numpy.uint8)
while True:
  t = time.time() / VELOCITY
  for i in range(PIXELS):
    #h = (i/PIXELS + t) % 1.0
    #data[i] = gamma(colorsys.hsv_to_rgb(h, 1.0, BRIGHTNESS))
    m = t * 10
    p = 7
    p2 = 5
    v = math.sin(m+(i/p))
    v2 = math.sin((-m)+(i/p))
    v3 = math.sin(m*3.5+(i/p2))
    r = (v+1)/2
    g = (v2+1)/2
    b = (v3+1)/2
    data[i] = gamma([r*255, g*255, b*255])
  ws2812.write2812(spi, data)
  time.sleep(0.05)

