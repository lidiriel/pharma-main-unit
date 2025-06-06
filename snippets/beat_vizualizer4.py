import numpy as np
import pyaudio
from collections import deque
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import argparse

# === Paramètres ===
parser = argparse.ArgumentParser()
parser.add_argument('--min_energy', type=float, default=1e9)
parser.add_argument('--min_freq', type=float, default=0.0)
parser.add_argument('--max_freq', type=float, default=6000.0)
parser.add_argument('--debug', action='store_true')
parser.set_defaults(debug=False)
args = parser.parse_args()

CHUNK = 1024
RATE = 44100
CHANNELS = 1
N_BANDS = 64
ENERGY_HISTORY = 43
DISPLAY_HISTORY = 100  # Nombre d’images affichées en mémoire
DEFAULT_C_FACTOR = 1.5

# === PyAudio setup ===
p = pyaudio.PyAudio()

def find_input_device(name_part="Loopback"):
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if name_part.lower() in info['name'].lower() and info['maxInputChannels'] > 0:
            return i
    return None

device_index = find_input_device("loopback_capture")
if device_index is None:
    raise RuntimeError("Périphérique d'entrée non trouvé.")

stream = p.open(format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK)

# === Bandes log ===
def log_frequency_bands(n_freqs=CHUNK, n_bands=N_BANDS):
    bins = [0]
    log_sizes = np.logspace(0, 1, num=n_bands, base=10)
    scaled_sizes = log_sizes / np.sum(log_sizes) * n_freqs
    band_sizes = np.round(scaled_sizes).astype(int)
    band_sizes[0] = 2
    band_sizes[-1] += n_freqs - np.sum(band_sizes)
    current = 0
    for size in band_sizes:
        bins.append(current + size)
        current += size
    return [(bins[i], bins[i + 1]) for i in range(len(bins) - 1)]

bands = log_frequency_bands()

def band_to_freq(index):
    return index * RATE / CHUNK

# Sélection bandes utiles
filtered_bands = []
filtered_indices = []
for i, (start, end) in enumerate(bands):
    start_freq = band_to_freq(start)
    end_freq = band_to_freq(end)
    if start_freq >= args.min_freq and end_freq <= args.max_freq:
        filtered_bands.append((start, end))
        filtered_indices.append(i)

# === Historique ===
energy_history = [deque(maxlen=ENERGY_HISTORY) for _ in range(N_BANDS)]
energy_display = deque(maxlen=DISPLAY_HISTORY)  # affichage temporel
beats_display = deque(maxlen=DISPLAY_HISTORY)   # affichage des beats

# === Matplotlib setup ===
fig, ax = plt.subplots(figsize=(10, 6))
img = ax.imshow(np.zeros((len(filtered_indices), DISPLAY_HISTORY)), 
                aspect='auto', origin='lower', interpolation='nearest', cmap='inferno')
ax.set_title("Énergie par bande de fréquence")
ax.set_xlabel("Temps (frames)")
ax.set_ylabel("Bandes")
plt.tight_layout()

def update_plot(frame):
    data = stream.read(CHUNK, exception_on_overflow=False)
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(samples, n=CHUNK))

    energies = []
    beats = []
    for idx, i in enumerate(filtered_indices):
        start, end = filtered_bands[idx]
        band_weight = (end - start) / CHUNK
        energy = band_weight * np.sum(spectrum[start:end] ** 2)
        energy_history[i].append(energy)
        mean = np.mean(energy_history[i])
        var = np.var(energy_history[i])
        cfactor = -15*var + 1.55
        beat = energy > cfactor * mean if energy > args.min_energy else False
        energies.append(energy)
        beats.append(1 if beat else 0)

    energy_display.append(energies)
    beats_display.append(beats)

    energy_matrix = np.array(energy_display).T
    beat_matrix = np.array(beats_display).T
    display_matrix = np.log1p(energy_matrix)  # Pour meilleure échelle visuelle
    display_matrix += beat_matrix * 2  # accentue les beats

    img.set_data(display_matrix)
    return [img]

ani = animation.FuncAnimation(fig, update_plot, interval=30)
plt.show()

# Cleanup à la fin
stream.stop_stream()
stream.close()
p.terminate()
