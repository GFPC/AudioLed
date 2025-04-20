import numpy as np
import pyaudio
import spidev
import ws2812
import colorsys

# Конфигурация
PIXELS = 90
MAX_BRIGHTNESS = 255
SPI_DEVICE = 1
CHUNK = 2 ** 11
RATE = 44100

# Настройки басс-визуализации
BASS_RANGE = (20, 200)
SMOOTHING_FACTOR = 0.2
MIN_BASS_THRESHOLD = 50
FIXED_MAX_BASS = 5000000  # Фиксированный максимальный уровень баса

# Инициализация устройств
spi = spidev.SpiDev()
spi.open(SPI_DEVICE, 0)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                input=True, frames_per_buffer=CHUNK)

print("** INITIALIZED **")


def calculate_bass_level(data, rate):
    """Расчёт уровня баса."""
    fft = np.fft.rfft(np.abs(data))
    freqs = np.fft.rfftfreq(len(data), 1.0 / rate)
    mask = (freqs >= BASS_RANGE[0]) & (freqs <= BASS_RANGE[1])
    return np.sum(np.abs(fft[mask]))


def smooth_value(current, target, factor):
    """Сглаживание значения."""
    return factor * target + (1 - factor) * current


def bass_to_color(bass_normalized):
    """Генерация цвета по уровню баса."""
    hue = 0.66 - (0.66 * bass_normalized)
    r, g, b = colorsys.hls_to_rgb(hue, 0.5, 1.0)
    brightness = bass_normalized ** 0.5  # Гамма-коррекция
    return (
        int(g * MAX_BRIGHTNESS * brightness),
        int(r * MAX_BRIGHTNESS * brightness),
        int(b * MAX_BRIGHTNESS * brightness)
    )


try:
    out = [[0, 0, 0] for _ in range(PIXELS)]
    smoothed_bass = 0

    while True:
        # Чтение данных
        data = np.frombuffer(
            stream.read(CHUNK, exception_on_overflow=False),
            dtype=np.int16
        )

        # Расчёт уровня баса
        bass_level = calculate_bass_level(data, RATE)

        # Нормализация к фиксированному диапазону
        bass_norm = min(bass_level / FIXED_MAX_BASS, 1.0)

        # Сглаживание
        smoothed_bass = smooth_value(smoothed_bass, bass_norm, SMOOTHING_FACTOR)

        # Генерация цвета
        if bass_level > MIN_BASS_THRESHOLD:
            color = bass_to_color(smoothed_bass)
        else:
            color = (0, 0, 0)

        # Обновление ленты
        for i in range(PIXELS):
            out[i] = color
        ws2812.write2812(spi, out)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    # Очистка
    stream.stop_stream()
    stream.close()
    p.terminate()
    ws2812.write2812(spi, [[0, 0, 0] for _ in range(PIXELS)])
    spi.close()