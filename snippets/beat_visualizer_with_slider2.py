import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.widgets as widgets
import pyaudio
from collections import deque

# === Paramètres audio ===
CHUNK = 1024
RATE = 44100
DEVICE_NAME = "loopback_capture"  # À adapter si besoin
CHANNELS = 1
N_BANDS = 64
ENERGY_HISTORY = 42
DEFAULT_VARIANCE_THRESHOLD = 150
DEFAULT_C_FACTOR = 200

# === Initialisation PyAudio ===
p = pyaudio.PyAudio()
# Sélection automatique d'un périphérique contenant "Loopback" ou autre
def find_input_device(name_part="Loopback"):
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if name_part.lower() in info['name'].lower() and info['maxInputChannels'] > 0:
            return i
    return None

device_index = find_input_device(DEVICE_NAME)
if device_index is None:
    raise RuntimeError("Périphérique d'entrée non trouvé.")

stream = p.open(format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK)

# === Historique énergie pour chaque bande ===
energy_history = [deque(maxlen=ENERGY_HISTORY) for _ in range(N_BANDS)]

# === Distribution logarithmique des fréquences ===
def log_frequency_bands(n_freqs=CHUNK, n_bands=N_BANDS):
    bins = [0]
    min_band_size = 2
    log_sizes = np.logspace(0, 1, num=n_bands, base=10)
    scaled_sizes = log_sizes / np.sum(log_sizes) * n_freqs
    band_sizes = np.round(scaled_sizes).astype(int)

    band_sizes[0] = 2
    diff = n_freqs - np.sum(band_sizes)
    band_sizes[-1] += diff

    current = 0
    for size in band_sizes:
        bins.append(current + size)
        current += size

    bands = [(bins[i], bins[i + 1]) for i in range(len(bins) - 1)]
    return bands, bins

bands, band_bins = log_frequency_bands()

# === Setup de la figure ===
fig, axs = plt.subplots(6, 1, figsize=(10, 10), gridspec_kw={'height_ratios': [1, 1, 1, 1, 0.2, 0.2]})

line_waveform, = axs[0].plot(np.zeros(CHUNK))
axs[0].set_title("Signal audio (temps)")

line_spectrum, = axs[1].plot(np.zeros(CHUNK//2 + 1))
axs[1].set_title("Spectre de fréquence (FFT)")

# Tracés des lignes verticales indiquant les bandes
for x in band_bins[1:-1]:
    axs[1].axvline(x=x, color='gray', linestyle='--', linewidth=0.5)

bar_energy = axs[2].bar(range(N_BANDS), [0]*N_BANDS, color='lightblue')
axs[2].set_ylim(0, np.log10(1e10 + 1))
axs[2].set_title("Énergie par bande (échelle log)")

bar_beats = axs[3].bar(range(N_BANDS), [0]*N_BANDS, color='gray')
axs[3].set_ylim(0, 1)
axs[3].set_title("Détection de Beat")

# === Sliders ===
plt.subplots_adjust(hspace=0.6)
slider_threshold = widgets.Slider(axs[4], 'Variance Threshold', 10, 1000, valinit=DEFAULT_VARIANCE_THRESHOLD)
slider_cfactor = widgets.Slider(axs[5], 'C Factor', 1, 250, valinit=DEFAULT_C_FACTOR)

# === Animation update ===
def update_plot(frame):
    data = stream.read(CHUNK, exception_on_overflow=False)
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(samples, n=CHUNK))

    band_energies = []
    beat_detected = []
    current_threshold = slider_threshold.val
    current_cfactor = slider_cfactor.val

    for i, (start, end) in enumerate(bands):
        band_weight = (end - start) / CHUNK
        energy = band_weight * np.sum(spectrum[start:end] ** 2)
        energy_history[i].append(energy)

        mean = np.mean(energy_history[i])
        var = np.var(energy_history[i])
        beat = energy > current_cfactor * mean and var > current_threshold

        band_energies.append(energy)
        beat_detected.append(1 if beat else 0)

        bar_beats[i].set_color('red' if beat else 'gray')

    line_waveform.set_ydata(samples)
    axs[0].set_ylim(-32000, 32000)

    line_spectrum.set_ydata(spectrum)
    axs[1].set_ylim(0, np.max(spectrum) + 100)

    for i, bar in enumerate(bar_energy):
        log_energy = np.log10(band_energies[i] + 1)
        bar.set_height(log_energy)
    for i, bar in enumerate(bar_beats):
        bar.set_height(beat_detected[i])

    return line_waveform, line_spectrum, bar_energy, bar_beats

# === Lancer l'animation ===
ani = animation.FuncAnimation(fig, update_plot, interval=30, blit=False)
plt.show()

# Cleanup
stream.stop_stream()
stream.close()
p.terminate()
