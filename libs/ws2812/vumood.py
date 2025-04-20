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

# Настройки басового детектора
BASS_RANGE = (20, 150)  # Четкий диапазон басовых частот
SMOOTHING_FACTOR = 0.3  # Плавность реакции
BASS_THRESHOLD = 1000  # Абсолютный порог баса (подбирается)
MIN_DB_DIFFERENCE = 10  # Минимальное превышение баса над средним

# Инициализация устройств
spi = spidev.SpiDev()
spi.open(SPI_DEVICE, 0)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                input=True, frames_per_buffer=CHUNK)

print("** BASS VISUALIZER INITIALIZED **")


def calculate_bass_power(data, rate):
    """Точный расчет мощности басовых частот в dB"""
    # Применяем оконную функцию для улучшения FFT
    window = np.hanning(len(data))
    windowed_data = data * window

    # Вычисляем FFT
    fft = np.fft.rfft(windowed_data)
    freqs = np.fft.rfftfreq(len(windowed_data), 1.0 / rate)

    # Разделяем на низкие (бас) и средние частоты
    bass_mask = (freqs >= BASS_RANGE[0]) & (freqs <= BASS_RANGE[1])
    mid_mask = (freqs > BASS_RANGE[1]) & (freqs < 1000)

    # Вычисляем энергию в dB
    bass_energy = 10 * np.log10(np.sum(np.abs(fft[bass_mask]) ** 2) + 1e-10)
    mid_energy = 10 * np.log10(np.sum(np.abs(fft[mid_mask]) ** 2) + 1e-10)

    return bass_energy, mid_energy


def is_bass_active(bass_db, mid_db):
    """Определяет, есть ли значимый бас"""
    return (bass_db > BASS_THRESHOLD) and ((bass_db - mid_db) > MIN_DB_DIFFERENCE)


def get_bass_color(bass_strength):
    """Генерация цвета от синего (тихий) до красного (громкий)"""
    hue = 0.66 - (0.66 * bass_strength)  # 0.66=синий, 0.0=красный
    r, g, b = colorsys.hls_to_rgb(hue, 0.5, 1.0)
    return (
        int(g * MAX_BRIGHTNESS),
        int(r * MAX_BRIGHTNESS),
        int(b * MAX_BRIGHTNESS)
    )


try:
    smoothed_bass = 0
    out = [[0, 0, 0] for _ in range(PIXELS)]

    while True:
        # Чтение аудиоданных
        data = np.frombuffer(
            stream.read(CHUNK, exception_on_overflow=False),
            dtype=np.int16
        )

        # Анализ частот
        bass_db, mid_db = calculate_bass_power(data, RATE)

        # Проверка наличия баса
        if is_bass_active(bass_db, mid_db):
            # Нормализация силы баса (0-1)
            bass_strength = min((bass_db - BASS_THRESHOLD) / 20, 1.0)
            smoothed_bass = smooth_value(smoothed_bass, bass_strength, SMOOTHING_FACTOR)
            color = get_bass_color(smoothed_bass)
        else:
            smoothed_bass = 0
            color = (0, 0, 0)

        # Обновление ленты
        for i in range(PIXELS):
            out[i] = color
        ws2812.write2812(spi, out)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    # Корректное завершение
    stream.stop_stream()
    stream.close()
    p.terminate()
    ws2812.write2812(spi, [[0, 0, 0] for _ in range(PIXELS)])
    spi.close()