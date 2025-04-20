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

# Настройки обработки звука
BASS_RANGE = (20, 200)  # Диапазон басовых частот
SMOOTHING_FACTOR = 0.25  # Коэффициент сглаживания
MIN_VOLUME_THRESHOLD = 0.01  # Минимальная громкость для реакции
BASS_RATIO_THRESHOLD = 0.3  # Минимальное отношение бас/общая громкость

# Инициализация устройств
spi = spidev.SpiDev()
spi.open(SPI_DEVICE, 0)

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                input=True, frames_per_buffer=CHUNK)

print("** INITIALIZED **")


class AudioProcessor:
    def __init__(self):
        self.smoothed_bass_ratio = 0
        self.smoothed_volume = 0
        self.last_active_time = 0

    def process_audio(self, data):
        # Расчет общего уровня громкости (RMS)
        rms = np.sqrt(np.mean(np.square(data.astype(np.float32))))

        # Расчет уровня баса (FFT)
        fft = np.fft.rfft(np.abs(data))
        freqs = np.fft.rfftfreq(len(data), 1.0 / RATE)
        bass_mask = (freqs >= BASS_RANGE[0]) & (freqs <= BASS_RANGE[1])
        bass_level = np.sum(np.abs(fft[bass_mask]))

        # Нормализация и расчет отношения баса к общей громкости
        bass_ratio = bass_level / (rms + 1e-10)  # Добавляем маленькое число чтобы избежать деления на 0

        # Сглаживание значений
        self.smoothed_volume = smooth_value(self.smoothed_volume, rms, SMOOTHING_FACTOR)
        self.smoothed_bass_ratio = smooth_value(self.smoothed_bass_ratio, bass_ratio, SMOOTHING_FACTOR)

        # Определение активности баса
        if self.smoothed_volume > MIN_VOLUME_THRESHOLD and self.smoothed_bass_ratio > BASS_RATIO_THRESHOLD:
            self.last_active_time = time.time()
            active = True
        else:
            active = time.time() - self.last_active_time < 1.0  # Задержка выключения 1 сек

        return active, self.smoothed_bass_ratio, self.smoothed_volume


def smooth_value(current, target, factor):
    return factor * target + (1 - factor) * current


def get_bass_color(bass_ratio, volume):
    """Генерация цвета на основе отношения баса и громкости"""
    # Нормализованный уровень баса (0-1)
    norm_bass = min(bass_ratio / 2.0, 1.0)  # Эмпирически подобранный делитель

    # Цвет от синего (0.66) до красного (0.0)
    hue = 0.66 - (0.66 * norm_bass)

    # Яркость зависит от общей громкости
    lightness = 0.1 + 0.7 * min(volume * 100, 1.0)

    # Конвертация в RGB
    r, g, b = colorsys.hls_to_rgb(hue, lightness, 1.0)
    return (
        int(g * MAX_BRIGHTNESS),
        int(r * MAX_BRIGHTNESS),
        int(b * MAX_BRIGHTNESS)
    )


try:
    audio_processor = AudioProcessor()
    out = [[0, 0, 0] for _ in range(PIXELS)]

    while True:
        # Чтение аудиоданных
        data = np.frombuffer(
            stream.read(CHUNK, exception_on_overflow=False),
            dtype=np.int16
        )

        # Обработка аудио
        active, bass_ratio, volume = audio_processor.process_audio(data)

        # Генерация цвета
        if active:
            color = get_bass_color(bass_ratio, volume)
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