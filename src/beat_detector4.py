import numpy as np
import pyaudio
from collections import deque
import time
from time import perf_counter

# === Paramètres audio ===
import argparse

parser = argparse.ArgumentParser(description="Détection de beats audio en console")
parser.add_argument('--min_freq', type=float, default=0.0, help="Fréquence minimale à analyser (Hz)")
parser.add_argument('--max_freq', type=float, default=6000.0, help="Fréquence maximale à analyser (Hz)")
parser.add_argument('--min_energy', type=float, default=1e9, help="Seuil minimal absolu d'énergie pour ignorer les bandes faibles")
parser.add_argument('--debug', action='store_true')
parser.set_defaults(debug=False)
args = parser.parse_args()

CHUNK = 1024
RATE = 44100
DEVICE_NAME = "loopback_capture"  # À adapter si besoin
CHANNELS = 1
N_BANDS = 64
ENERGY_HISTORY = 42

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
    return bands

bands = log_frequency_bands()

# Filtrage des bandes selon l'intervalle de fréquence
def band_to_freq(index):
    return index * RATE / CHUNK

filtered_bands = []
filtered_indices = []
for i, (start, end) in enumerate(bands):
    start_freq = band_to_freq(start)
    end_freq = band_to_freq(end)
    if start_freq >= args.min_freq and end_freq <= args.max_freq:
        filtered_bands.append((start, end))
        filtered_indices.append(i)


prev_beat = perf_counter()

# === Boucle principale console ===
try:
    print("[INFO] Analyse en cours... Appuyez sur Ctrl+C pour quitter.")
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        spectrum = np.abs(np.fft.rfft(samples, n=CHUNK))

        beat_detected = [0]*N_BANDS
        #cfactor = []
        for idx, i in enumerate(filtered_indices):
            start, end = filtered_bands[idx]
            band_weight = (end - start) / CHUNK
            energy = band_weight * np.sum(spectrum[start:end] ** 2)
            if energy < args.min_energy:
                beat = False
                energy_history[i].append(energy)
                #beat_detected[i] = 0
                continue
            energy_history[i].append(energy)

            mean = np.mean(energy_history[i])
            var = np.var(energy_history[i])
            current_cfactor = -15*var+1.55
            beat = energy > current_cfactor * mean
            beat_detected[i] = (1 if beat else 0)
            #cfactor.append(current_cfactor)
            if args.debug:
                print(f"Bande {i:02d} | Energie: {energy_history[i][-1]:.2e} | Moyenne: {mean:.2e} | Variance: {var:.2e} | Cfact: {current_cfactor:.2e} | Beat: {'OUI' if beat_detected[i] else '-'}")
               
        if sum(beat_detected):
            curr_time = perf_counter()
            if curr_time - prev_beat > 60/180: # 180 BPM max
                # reset the timer
                prev_beat = curr_time
            else:
                beat_detected = [0] * N_BANDS
        

        
        # Affichage console : une ligne de 32 caractères représentant les beats
        visual = ''.join(['#' if i in filtered_indices and beat_detected[i] else '-' for i in range(N_BANDS)])
        print(visual)
        if args.debug:
             print('-' * 80)
        

        #time.sleep(0.03)  # ~30 FPS

except KeyboardInterrupt:
    print("\n[INFO] Arrêt de l'analyse.")
    stream.stop_stream()
    stream.close()
    p.terminate()
