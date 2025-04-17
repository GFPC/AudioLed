import numpy as np
import pyaudio
import spidev
import ws2812
import colorsys

# Конфигурация
PIXELS = 90
MAX_BRIGHTNESS = 255  # Максимальная яркость (0-255)
SPI_DEVICE = 1
CHUNK = 2 ** 11
RATE = 44100

# Настройки басс-визуализации
BASS_RANGE = (20, 200)  # Диапазон частот баса
SMOOTHING_FACTOR = 0.2  # Коэффициент сглаживания
MIN_BASS_THRESHOLD = 50  # Минимальный уровень баса для реакции
DYNAMIC_RANGE = 30  # Динамический диапазон в dB

# Инициализация SPI
spi = spidev.SpiDev()
spi.open(SPI_DEVICE, 0)

# Инициализация аудиопотока
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                input=True, frames_per_buffer=CHUNK)

print("** INITIALIZED **")

# Переменные для обработки звука
smoothed_bass = 0
peak_bass = 0
dynamic_max = MIN_BASS_THRESHOLD * 10  # Начальное значение динамического максимума


def calculate_bass_level(data, rate):
    """Вычисляет уровень басса в dB."""
    fft = np.fft.rfft(np.abs(data))
    freqs = np.fft.rfftfreq(len(data), 1.0 / rate)

    mask = (freqs >= BASS_RANGE[0]) & (freqs <= BASS_RANGE[1])
    bass_energy = np.sum(np.abs(fft[mask]))

    # Преобразуем в dB (избегаем log(0))
    return 10 * np.log10(bass_energy + 1e-10)


def smooth_value(current, target, factor):
    """Экспоненциальное сглаживание значения."""
    return factor * target + (1 - factor) * current


def update_dynamic_range(current_level):
    """Адаптивно обновляет динамический диапазон."""
    global dynamic_max
    dynamic_max = smooth_value(dynamic_max, current_level * 1.5, 0.01)
    return max(MIN_BASS_THRESHOLD * 2, dynamic_max)


def normalize_bass_level(bass_db, dynamic_max):
    """Нормализует уровень басса к 0-1 с учетом динамического диапазона."""
    bass_normalized = (bass_db - (dynamic_max - DYNAMIC_RANGE)) / DYNAMIC_RANGE
    return np.clip(bass_normalized, 0, 1)


def bass_to_color(bass_normalized):
    """Преобразует уровень басса в цвет с яркостью, соответствующей громкости."""
    # Цветовая схема: от синего (тихий) до красного (громкий)
    hue = 0.66 - (0.66 * bass_normalized)  # 0.66 - синий, 0.0 - красный

    # Фиксированная насыщенность
    saturation = 1.0

    # Яркость прямо пропорциональна уровню баса
    lightness = 0.1 + 0.7 * bass_normalized

    # Конвертация HSL to RGB
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)

    # Применение общей яркости
    brightness_factor = bass_normalized ** 2  # Квадрат для более естественного восприятия
    return (
        int(g * MAX_BRIGHTNESS * brightness_factor),
        int(r * MAX_BRIGHTNESS * brightness_factor),
        int(b * MAX_BRIGHTNESS * brightness_factor)
    )


try:
    out = [[0, 0, 0] for _ in range(PIXELS)]

    while True:
        # Чтение аудиоданных
        data = np.frombuffer(
            stream.read(CHUNK, exception_on_overflow=False),
            dtype=np.int16
        )

        # Вычисление уровня басса в dB
        bass_level = calculate_bass_level(data, RATE)

        # Обновление динамического диапазона
        dynamic_max = update_dynamic_range(bass_level)

        # Нормализация уровня басса
        bass_norm = normalize_bass_level(bass_level, dynamic_max)

        print("BASSLEVEL:", bass_level, "DB", bass_norm, "MAX", dynamic_max)

        # Если басс ниже порога - выключаем светодиоды
        if bass_level < MIN_BASS_THRESHOLD:
            ws2812.write2812(spi, [[0, 0, 0] for _ in range(PIXELS)])
            continue

        # Сглаживание уровня басса
        smoothed_bass = smooth_value(smoothed_bass, bass_norm, SMOOTHING_FACTOR)

        # Генерация цвета с яркостью, соответствующей громкости
        color = bass_to_color(smoothed_bass)

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