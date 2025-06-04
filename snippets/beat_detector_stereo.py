import numpy as np
import pyaudio
from collections import deque
import time
from time import perf_counter
import time

# === Paramètres audio ===
import argparse

parser = argparse.ArgumentParser(description="Détection de beats audio en console")
parser.add_argument('--min_freq', type=float, default=0.0, help="Fréquence minimale à analyser (Hz)")
parser.add_argument('--max_freq', type=float, default=6000.0, help="Fréquence maximale à analyser (Hz)")
parser.add_argument('--min_energy', type=float, default=1e5, help="Seuil minimal absolu d'énergie pour ignorer les bandes faibles")
parser.add_argument('--c_factor', type=float, default=2, help="Seuil du ratio E/<E> de détection")
parser.add_argument('--debug', action='store_true')
parser.set_defaults(debug=False)
args = parser.parse_args()

CHUNK = 1024
RATE = 96000
SAMPLE_FORMAT = pyaudio.paInt32
#DEVICE_NAME = "ADCWM8782"
DEVICE_NAME = "adc_sv"
CHANNELS = 2
N_BANDS = 32
ENERGY_HISTORY = 42

# === Initialisation PyAudio ===
p = pyaudio.PyAudio()
# Sélection automatique d'un périphérique contenant "Loopback" ou autre
def find_input_device(name_part="Loopback"):
    print(f"search for device {name_part}")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"device {i} info {info['name']}")
        if name_part.lower() in info['name'].lower() and info['maxInputChannels'] > 0:
            return i
    return None

device_index = find_input_device(DEVICE_NAME)
if device_index is None:
    raise RuntimeError("Périphérique d'entrée non trouvé.")

stream = p.open(format=SAMPLE_FORMAT,
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
print(f"bands = {bands}")

# Band filtering according to frequency
def band_to_freq(index):
    return index * RATE / CHUNK

filtered_bands = []
filtered_indices = []
filtered_frequency = []
for i, (start, end) in enumerate(bands):
    start_freq = band_to_freq(start)
    end_freq = band_to_freq(end)
    if (start_freq <= args.min_freq and args.min_freq <= end_freq) or \
            (args.min_freq <= start_freq and end_freq <= args.max_freq) or \
            (start_freq <= args.max_freq and args.max_freq <= end_freq):
        filtered_bands.append((start, end))
        filtered_indices.append(i)
        filtered_frequency.append((start_freq,end_freq))

print("### filtered bands")
print(f"bands = {filtered_bands}")
print(f"frequency = {filtered_frequency}")
print(f"indices (band number) = {filtered_indices}")
      

prev_beat = perf_counter()
beats_empty = [0]*N_BANDS 
# Main loop on consol
try:
    print("[INFO] Analyse en cours... Appuyez sur Ctrl+C pour quitter.")
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=np.int32).astype(np.float32)
        samples = samples.reshape(-1, CHANNELS)
        # Mean of channels
        mono_samples = np.mean(samples, axis=1)
        
        spectrum = np.abs(np.fft.rfft(mono_samples, n=CHUNK))

        beats_detected = beats_empty
        #cfactor = []
        for iband in filtered_indices:
            start, end = bands[iband]
            band_weight = ((end - start) + 1) / CHUNK
            energy = band_weight * np.sum(spectrum[start:end] ** 2)
            if energy < args.min_energy:
                energy_history[iband].append(energy)
                beats_detected[iband] = 0
                continue
            energy_history[iband].append(energy)

            mean = np.mean(energy_history[iband])
            var = np.var(energy_history[iband])
            ratio = energy / mean
            #current_cfactor = -15*var+1.55
            beats_detected[iband] = (1 if ratio > args.c_factor  else 0)
            if args.debug:
                print(f"Bande {iband:02d} | Energie: {energy_history[iband][-1]:.2e} | Moyenne: {mean:.2e} | Ratio {ratio:.2e} | Variance: {var:.2e} | Beat: {'OUI' if beats_detected[iband] else '-'}")
        if sum(beats_detected):
           curr_time = perf_counter()
           if curr_time - prev_beat < 60/180: # 180 BPM max
               beats_detected = beats_empty
           else:
               prev_beat = curr_time

        
        # Affichage console : une ligne de 32 caractères représentant les beats
        visual = ''.join(['#' if beats_detected[i] else '-' for i in range(N_BANDS)])
        print(visual)

        time.sleep(0.03)  # ~30 FPS

except KeyboardInterrupt:
    print("\n[INFO] Arrêt de l'analyse.")
    stream.stop_stream()
    stream.close()
    p.terminate()
