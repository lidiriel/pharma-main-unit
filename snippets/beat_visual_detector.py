import numpy as np
import pyaudio
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque

# ==== PARAMÈTRES ====
CHUNK = 1024
RATE = 44100
DEVICE_NAME = "loopback_capture"
N_BANDS = 32
HISTORY = 42

# ==== INITIALISATION ====
p = pyaudio.PyAudio()

def find_input_device(name_part="Loopback"):
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if name_part.lower() in info['name'].lower() and info['maxInputChannels'] > 0:
            return i
    return None

device_index = find_input_device(DEVICE_NAME)
if device_index is None:
    raise RuntimeError("Périphérique d'entrée non trouvé.")

stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK)

energy_history = [deque(maxlen=HISTORY) for _ in range(N_BANDS)]
buffer = np.zeros(CHUNK)

# ==== VISU ====
fig, (ax_signal, ax_beats) = plt.subplots(2, 1, figsize=(10, 6))

# 1. Signal brut (oscillogramme)
line_signal, = ax_signal.plot(buffer)
ax_signal.set_ylim(-1, 1)
ax_signal.set_title("Signal audio")
ax_signal.set_xlabel("Échantillons")
ax_signal.set_ylabel("Amplitude")

# 2. Beats détectés (barres par bande)
bars = ax_beats.bar(range(N_BANDS), [0]*N_BANDS)
ax_beats.set_ylim(0, 1.5)
ax_beats.set_title("Détection de beat par bande")
ax_beats.set_xlabel("Bande de fréquence")
ax_beats.set_ylabel("État (0/1)")

def update_plot(frame):
    global buffer

    # Lire et stocker dans buffer
    data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.float32)
    buffer = data
    line_signal.set_ydata(buffer)

    # FFT et découpage
    fft_data = np.abs(np.fft.rfft(data))
    band_size = len(fft_data) // N_BANDS
    beats = []

    for i in range(N_BANDS):
        start = i * band_size
        end = start + band_size
        band_energy = np.sum(fft_data[start:end] ** 2)
        history = energy_history[i]
        mean_energy = np.mean(history) if history else 0
        is_beat = band_energy > mean_energy if mean_energy > 0 else False
        beats.append(1.0 if is_beat else 0.0)
        history.append(band_energy)

    # Mise à jour des barres
    for bar, val in zip(bars, beats):
        bar.set_height(val)
        bar.set_color("tab:red" if val > 0 else "tab:gray")

    return line_signal, *bars

ani = FuncAnimation(fig, update_plot, interval=30, blit=False)
plt.tight_layout()
plt.show()

# Cleanup après fermeture fenêtre
stream.stop_stream()
stream.close()
p.terminate()
