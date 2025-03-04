import numpy as np, pyaudio
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
# Параметры сглаживания (EMA)
SMOOTHING_FACTOR = 1  # Коэффициент сглаживания (0 < SMOOTHING_FACTOR < 1)
smoothed_bass_level = 0.1  # Начальное значение для сглаженного уровня басса


def calculate_bass_level(data, rate):
    """
    Вычисляет уровень басса (низких частот) из аудиоданных.
    """
    # Применение FFT для перевода в частотную область
    fft_data = np.fft.fft(data)
    freqs = np.fft.fftfreq(len(fft_data), 1.0 / rate)

    # Фильтрация низких частот (басс: 20-200 Гц)
    bass_range = (20,58)
    mask = (freqs >= bass_range[0]) & (freqs <= bass_range[1])
    fft_filtered = fft_data[mask]

    # Вычисление амплитуды басса
    bass_amplitude = np.abs(fft_filtered).mean()
    return bass_amplitude


def map_value(value, in_min, in_max, out_min, out_max):
    """
    Преобразует значение из одного диапазона в другой.
    """
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def smooth_value(current_value, target_value, smoothing_factor):
    """
    Сглаживает значение с использованием экспоненциального скользящего среднего (EMA).
    """
    return smoothing_factor * target_value + (1 - smoothing_factor) * current_value


try:
    out = [[0,0,0] for i in range(PIXELS)]
    while True:
        # Чтение данных из аудиопотока
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)

        # Вычисление уровня басса
        bass_level = calculate_bass_level(audio_data, RATE)

        # Сглаживание уровня басса
        smoothed_bass_level = smooth_value(smoothed_bass_level, bass_level, SMOOTHING_FACTOR)

        # Нормализация уровня басса к диапазону 0-255
        brightness = int(map_value(smoothed_bass_level, 0, 10000000, 10, 255))  # Настройте 5000 под ваш сигнал
        brightness = np.clip(brightness, 0, 255)  # Ограничение значения

        # Смена цвета в зависимости от уровня басса
        # Например, от синего (низкий басс) до красного (высокий басс)
        red = 0#brightness
        green = brightness
        blue = 0#brightness

        for i in range(PIXELS):
            out[i] = [red, green, blue]
        ws2812.write2812(spi, out)

except KeyboardInterrupt:
    pass

finally:
    # Очистка
    stream.stop_stream()
    stream.close()
    p.terminate()
    ws2812.write2812(spi, [[0, 0, 0]*PIXELS])