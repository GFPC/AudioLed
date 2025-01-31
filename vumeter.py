# amixer set Mic1 cap
# amixer set 'Mic1 Boost' 100
# amixer set 'ADC Gain' 100
# arecord -vv /dev/null

import signal, sys
import pyaudio, numpy
import spidev, ws2812

PIXELS = 150
DIVIDER = 10000/PIXELS

spi = spidev.SpiDev()
spi.open(0,0)

CHUNK = 2**11
RATE = 44100

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,channels=1,rate=RATE,input=True,
              frames_per_buffer=CHUNK)

def signal_handler(sig, frame):
  print('You pressed Ctrl+C!')
  #clear leds
  data = numpy.zeros((PIXELS, 3), dtype=numpy.uint8)
  ws2812.write2812(spi, data)
  #stop audio
  stream.stop_stream()
  stream.close()
  p.terminate()
  sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

out = numpy.zeros((PIXELS, 3), dtype=int)
while True:
#for i in range(int(10*44100/1024)): #go for a few seconds
  data = numpy.fromstring(stream.read(CHUNK), dtype=numpy.int16)
  #peak=np.average(np.abs(data))*2
  #bars="#"*int(50*peak/2**16)
  peak = numpy.amax(numpy.abs(data))
  bars = "#" * int(peak/200)
  #print("%04d %05d %s"%(i,peak,bars))
  #print("%05d %s"%(peak,bars))
  out.fill(0)
  out[0:int(peak/200)] = (100, 0, 0)
  ws2812.write2812(spi, out)

