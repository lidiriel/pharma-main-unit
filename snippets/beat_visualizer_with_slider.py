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
N_BANDS = 32
ENERGY_HISTORY = 42
DEFAULT_VARIANCE_THRESHOLD = 150
C_FACTOR = 200

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
def log_frequency_bands(n_freqs=CHUNK//2+1, n_bands=N_BANDS):
    log_bins = np.logspace(np.log10(2), np.log10(n_freqs), num=n_bands + 1, base=10).astype(int)
    log_bins = np.clip(log_bins, 0, n_freqs - 1)
    return [(log_bins[i], log_bins[i+1]) for i in range(n_bands)]

bands = log_frequency_bands()

# === Setup de la figure ===
fig, axs = plt.subplots(5, 1, figsize=(10, 9), gridspec_kw={'height_ratios': [1, 1, 1, 1, 0.2]})

line_waveform, = axs[0].plot(np.zeros(CHUNK))
axs[0].set_title("Signal audio (temps)")

line_spectrum, = axs[1].plot(np.zeros(CHUNK//2 + 1))
axs[1].set_title("Spectre de fréquence (FFT)")

bar_energy = axs[2].bar(range(N_BANDS), [0]*N_BANDS, color='lightblue')
axs[2].set_ylim(0, 1e10)
axs[2].set_title("Énergie par bande")

bar_beats = axs[3].bar(range(N_BANDS), [0]*N_BANDS, color='gray')
axs[3].set_ylim(0, 1)
axs[3].set_title("Détection de Beat")

# === Slider pour ajuster VARIANCE_THRESHOLD ===
ax_slider = axs[4]
plt.subplots_adjust(hspace=0.6)
slider = widgets.Slider(ax_slider, 'Variance Threshold', 10, 1000, valinit=DEFAULT_VARIANCE_THRESHOLD)
slider_val = [DEFAULT_VARIANCE_THRESHOLD]

# === Animation update ===
def update_plot(frame):
    data = stream.read(CHUNK, exception_on_overflow=False)
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(samples, n=CHUNK))

    band_energies = []
    beat_detected = []
    current_threshold = slider.val

    for i, (start, end) in enumerate(bands):
        energy = (N_BANDS/CHUNK) * np.sum(spectrum[start:end] ** 2)
        energy_history[i].append(energy)

        mean = np.mean(energy_history[i])
        var = np.var(energy_history[i])
        beat = energy > C_FACTOR*mean and var > current_threshold

        band_energies.append(energy)
        beat_detected.append(1 if beat else 0)

        bar_beats[i].set_color('red' if beat else 'gray')

    # Mise à jour des tracés
    line_waveform.set_ydata(samples)
    axs[0].set_ylim(-32000, 32000)

    line_spectrum.set_ydata(spectrum)
    axs[1].set_ylim(0, np.max(spectrum) + 100)

    for i, bar in enumerate(bar_energy):
        bar.set_height(band_energies[i])
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
