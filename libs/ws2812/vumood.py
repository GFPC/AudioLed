import numpy as np
import pyaudio
import spidev
import ws2812
import colorsys
import time

# Конфигурация
PIXELS = 90
MAX_BRIGHTNESS = 255
SPI_DEVICE = 1
CHUNK = 2 ** 11
RATE = 44100

# Настройки басс-визуализации
BASS_RANGE = (20, 200)
SMOOTHING_FACTOR = 0.3
MIN_BASS_THRESHOLD = 1000  # Порог для включения подсветки
FIXED_MAX_BASS = 3000000  # Фиксированный максимум для нормализации
DECAY_TIME = 0.5  # Время затухания (секунды)

# Инициализация устройств
spi = spidev.SpiDev()
spi.open(SPI_DEVICE, 0)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                input=True, frames_per_buffer=CHUNK)

print("** INITIALIZED **")


class BassTracker:
    def __init__(self):
        self.smoothed_bass = 0
        self.last_active_time = 0
        self.active = False

    def update(self, current_bass):
        # Проверка превышения порога
        if current_bass > MIN_BASS_THRESHOLD:
            self.last_active_time = time.time()
            self.active = True

        # Проверка времени без активности
        elif time.time() - self.last_active_time > DECAY_TIME:
            self.active = False

        # Сглаживание только при активности
        if self.active:
            norm_bass = min(current_bass / FIXED_MAX_BASS, 1.0)
            self.smoothed_bass = smooth_value(self.smoothed_bass, norm_bass, SMOOTHING_FACTOR)
        else:
            self.smoothed_bass = max(0, self.smoothed_bass - 0.05)  # Плавное затухание

        return self.smoothed_bass if self.active else 0


def calculate_bass_level(data, rate):
    """Точный расчет уровня баса с FFT."""
    fft = np.fft.rfft(np.abs(data))
    freqs = np.fft.rfftfreq(len(data), 1.0 / rate)
    mask = (freqs >= BASS_RANGE[0]) & (freqs <= BASS_RANGE[1])
    return np.sum(np.abs(fft[mask]))


def smooth_value(current, target, factor):
    """Экспоненциальное сглаживание."""
    return factor * target + (1 - factor) * current


def bass_to_color(bass_normalized):
    """Генерация цвета с улучшенной яркостью."""
    hue = 0.66 - (0.66 * bass_normalized)  # От синего к красному
    saturation = 1.0
    lightness = 0.3 + 0.7 * bass_normalized  # Яркость зависит от баса

    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return (
        int(g * MAX_BRIGHTNESS),
        int(r * MAX_BRIGHTNESS),
        int(b * MAX_BRIGHTNESS)
    )


try:
    tracker = BassTracker()
    out = [[0, 0, 0] for _ in range(PIXELS)]

    while True:
        # Чтение аудиоданных
        data = np.frombuffer(
            stream.read(CHUNK, exception_on_overflow=False),
            dtype=np.int16
        )

        # Расчет уровня баса
        bass_level = calculate_bass_level(data, RATE)

        # Обновление состояния
        smoothed_level = tracker.update(bass_level)

        # Генерация цвета
        if smoothed_level > 0:
            color = bass_to_color(smoothed_level)
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