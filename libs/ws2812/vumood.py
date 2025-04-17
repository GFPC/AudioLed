import numpy as np
import pyaudio
import spidev
import ws2812
import colorsys

# Конфигурация
PIXELS = 90
BRIGHTNESS = 255
VELOCITY = 10
SPI_DEVICE = 1
CHUNK = 2 ** 11
RATE = 44100

# Настройки басс-визуализации
BASS_RANGE = (20, 200)  # Диапазон частот баса
SMOOTHING_FACTOR = 0.3  # Коэффициент сглаживания (0.1-0.5 для плавности)
MAX_HISTORY = 5  # Глубина истории для пикового детектора

# Инициализация SPI
spi = spidev.SpiDev()
spi.open(SPI_DEVICE, 0)

# Инициализация аудиопотока
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                input=True, frames_per_buffer=CHUNK)

print("** INITIALIZED **")

# Переменные для сглаживания и истории
smoothed_bass = 0
bass_history = []
peak_bass = 0


def calculate_bass_level(data, rate):
    """Вычисляет уровень басса с помощью БПФ."""
    fft = np.fft.rfft(np.abs(data))
    freqs = np.fft.rfftfreq(len(data), 1.0 / rate)

    mask = (freqs >= BASS_RANGE[0]) & (freqs <= BASS_RANGE[1])
    bass_energy = np.sum(np.abs(fft[mask]))

    return bass_energy


def smooth_value(current, target, factor):
    """Экспоненциальное сглаживание значения."""
    return factor * target + (1 - factor) * current


def update_peak_detector(value, history, max_history):
    """Обновляет детектор пиков с историей значений."""
    history.append(value)
    if len(history) > max_history:
        history.pop(0)
    return max(history)


def bass_to_color(bass_normalized, peak_normalized):
    """Преобразует уровень басса в цвет на основе HSL."""
    # Базовый цвет (от фиолетового (0.8) до красного (0.0))
    hue = 0.8 - (0.8 * bass_normalized)
    hue = max(0.0, min(0.8, hue))

    # Насыщенность - максимальная
    saturation = 1.0

    # Яркость зависит от нормализованного басса и пика
    lightness = 0.1 + (0.7 * bass_normalized) + (0.2 * peak_normalized)
    lightness = max(0.1, min(0.9, lightness))

    # Конвертируем HSL в RGB
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)

    return int(g * 255), int(r * 255), int(b * 255)


try:
    out = [[0, 0, 0] for _ in range(PIXELS)]

    while True:
        # Чтение аудиоданных
        data = np.frombuffer(
            stream.read(CHUNK, exception_on_overflow=False),
            dtype=np.int16
        )

        # Вычисление уровня басса
        bass_level = calculate_bass_level(data, RATE)

        # Сглаживание и обновление истории
        smoothed_bass = smooth_value(smoothed_bass, bass_level, SMOOTHING_FACTOR)
        peak_bass = update_peak_detector(smoothed_bass, bass_history, MAX_HISTORY)

        # Нормализация (динамический диапазон)
        max_bass = max(1000, peak_bass * 1.2)  # Автоподстройка под громкость
        bass_norm = min(smoothed_bass / max_bass, 1.0)
        peak_norm = min(peak_bass / max_bass, 1.0)

        # Генерация цвета
        color = bass_to_color(bass_norm, peak_norm)

        # Обновление всех светодиодов
        for i in range(PIXELS):
            out[i] = color

        # Отправка на ленту
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