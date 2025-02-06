import numpy, pyaudio
import signal, sys, time, math
import spidev, ws2812

PIXELS = 90
BRIGHTNESS = 255
VELOCITY = 10
SPI_DEVICE = 1

spi = spidev.SpiDev()
spi.open(SPI_DEVICE, 0)

# CHUNK = 2**11
CHUNK = 2 ** 11
RATE = 44100

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,channels=1,rate=RATE,input=True,frames_per_buffer=CHUNK)

print("**INITIALIZED**")
def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    # clear leds
    data = numpy.zeros((PIXELS, 3), dtype=numpy.uint8)
    ws2812.write2812(spi, data)
    # stop audio
    stream.stop_stream()
    stream.close()
    p.terminate()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

def calculate_amplitude(data, rate, freq_range):
    # Применение FFT
    fft_data = numpy.fft.fft(data)
    freqs = numpy.fft.fftfreq(len(fft_data), 1.0 / rate)

    # Фильтрация частот в заданном диапазоне
    mask = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
    fft_filtered = fft_data[mask]

    # Вычисление амплитуды
    amplitude = numpy.abs(fft_filtered).mean()
    return amplitude
def HexToRGB(hex, brightness=255):
    return tuple(int(hex[i:i + 2], 16) * brightness / 255 for i in (0, 2, 4))

freq_bars = [(0, 2444), (2444, 4888), (4888, 7332), (7332, 9776), (9776, 12220), (12220, 14664), (14664, 17108), (17108, 19552), (19552, 22000)]
out = numpy.zeros((PIXELS, 3), dtype=numpy.uint8)
while True:
    t = time.time() / VELOCITY
    data = numpy.frombuffer(stream.read(CHUNK), dtype=numpy.int16)
    peak = numpy.amax(numpy.abs(data))
    bass_amp = calculate_amplitude(data, RATE, [0, 58])
    for i in range(PIXELS):
        color = HexToRGB("ffffff", int(i))
        out[i] = color
    """amplitudes = [ calculate_amplitude(data, RATE, freq_bars[i]) for i in range(len(freq_bars))]
    print(amplitudes)
    for i in range(len(amplitudes)):
        color = HexToRGB("ffffff", int(i))
        for k in range(10):
            out[i * 10 + k] = color"""
    ws2812.write2812(spi, out)
    time.sleep(0.05)
