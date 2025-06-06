import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pyaudio
from collections import deque

# === Paramètres ===
CHUNK = 1024
RATE = 44100
CHANNELS = 1
N_BANDS = 32
ENERGY_HISTORY = 43
DISPLAY_HISTORY = 100  # nb frames en X

# === Initialisation audio ===
p = pyaudio.PyAudio()

def find_input_device(name_part="loopback"):
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if name_part.lower() in info["name"].lower() and info["maxInputChannels"] > 0:
            print(f"[INFO] Périphérique trouvé : {info['name']}")
            return i
    raise RuntimeError("Périphérique 'loopback' non trouvé")

device_index = find_input_device("loopback")
stream = p.open(format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK)

# === Bandes logarithmiques ===
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

# === Historique pour affichage et détection ===
energy_history = [deque(maxlen=ENERGY_HISTORY) for _ in range(N_BANDS)]
energy_display = deque(maxlen=DISPLAY_HISTORY)
beats_display = deque(maxlen=DISPLAY_HISTORY)

# === Matplotlib setup ===
energy_display = deque([np.zeros(N_BANDS) for _ in range(DISPLAY_HISTORY)], maxlen=DISPLAY_HISTORY)
beats_display = deque([np.zeros(N_BANDS) for _ in range(DISPLAY_HISTORY)], maxlen=DISPLAY_HISTORY)

fig, ax = plt.subplots(figsize=(10, 6))
energy_matrix = np.array(energy_display).T
beat_matrix = np.array(beats_display).T

img = ax.imshow(energy_matrix, 
                aspect='auto', origin='lower', interpolation='nearest', cmap='inferno', vmin=0, vmax=10)

scatter = ax.imshow(beat_matrix, 
                    aspect='auto', origin='lower', interpolation='nearest', cmap='Greens', alpha=0.5, vmin=0, vmax=1)

ax.set_title("Énergie + Beats par bande")
ax.set_xlabel("Temps")
ax.set_ylabel("Bandes")
plt.tight_layout()


def update_plot(frame):
    print(".", end="", flush=True)  # Pour voir si ça tourne
    data = stream.read(CHUNK, exception_on_overflow=False)
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(samples))

    energies = []
    beats = []
    for i, (start, end) in enumerate(bands):
        band_weight = (end - start) / CHUNK
        energy = band_weight * np.sum(spectrum[start:end] ** 2)
        energy_history[i].append(energy)

        mean = np.mean(energy_history[i])
        var = np.var(energy_history[i])
        cfactor = -15 * var + 1.55
        beat = energy > cfactor * mean if energy > 1e6 else False

        energies.append(np.log1p(energy))
        beats.append(1 if beat else 0)

    energy_display.append(energies)
    beats_display.append(beats)

    energy_matrix = np.array(energy_display).T
    beat_matrix = np.array(beats_display).T

    img.set_data(energy_matrix)
    scatter.set_data(beat_matrix)
    return [img, scatter]


ani = animation.FuncAnimation(fig, update_plot, interval=30)
plt.show()

# Cleanup
stream.stop_stream()
stream.close()
p.terminate()
