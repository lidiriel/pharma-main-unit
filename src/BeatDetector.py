import threading
import logging
import time
import pyaudio
from time import perf_counter
import numpy as np
import json
from collections import deque
from Pins import PINS
import RPi.GPIO as GPIO
from threading import Thread

""" I2S ADC parameters
    Algo parameters
"""
CHUNK = 2048
RATE = 96000
SAMPLE_FORMAT = pyaudio.paInt32
CHANNELS = 2
N_BANDS = 32
ENERGY_HISTORY = 42

REGISTER_LED = 0
SEQ_NAME = "sequence1"

def visual_beat():
    GPIO.output(PINS['BEAT'], GPIO.HIGH)
    time.sleep(0.02)
    GPIO.output(PINS['BEAT'], GPIO.LOW)

class BeatDetector(threading.Thread):
    def __init__(self, config, queue):
        super().__init__()
        self.config = config
        self.queue = queue
        self.pa = pyaudio.PyAudio()
        self.logger = logging.getLogger('BeatDetector')
        self.logger.setLevel(logging.DEBUG)
        self.clk_id = time.CLOCK_REALTIME
        
    
    def find_input_device(self, name="Loopback"):
        self.logger.info(f"search for device {name}")
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            self.logger.debug(f"device {i} info {info['name']}")
            if name.lower() in info['name'].lower() and info['maxInputChannels'] > 0:
                return i
        return None
        
    # === logarithm frequency distribution ===
    def log_frequency_bands(self, n_freqs=CHUNK, n_bands=N_BANDS):
        bins = [0]
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
        
    def run(self):
        # READ sequence
        data = None
        try:
            with open(self.config.patterns_file) as f:
                data = json.load(f)
                self.logger.info(f"JSON patterns file content : {data}")
        except FileNotFoundError:
            self.logger.error(f"Error: File not found {self.config.patterns_file}")
        except json.JSONDecodeError:
            self.logger.error(f"Error Invalid JSON content {self.config.patterns_file}")
        except Exception as e:
            self.logger.error(f"Unexpected error : {e}")
        device_name = self.config.beat_device_name
        device_index = self.find_input_device(name=device_name)
        if device_index is None:
            self.logger.error(f"Périphérique d'entrée {device_name} non trouvé. Check asoundrc")
            raise RuntimeError("Périphérique d'entrée {device_name} non trouvé. Check asoundrc")


        stream = self.pa.open(format=SAMPLE_FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK)

        # === Energy history for each band ===
        energy_history = [deque(maxlen=ENERGY_HISTORY) for _ in range(N_BANDS)]

        bands = self.log_frequency_bands()
        self.logger.debug(f"bands = {bands}")
        
        # Band filtering according to frequency
        def band_to_freq(index):
            return index * RATE / CHUNK
        
        filtered_bands = []
        filtered_indices = []
        filtered_frequency = []
        band_weight = []
        filtered_band_weight = []
        for i, (start, end) in enumerate(bands):
            start_freq = band_to_freq(start)
            end_freq = band_to_freq(end)
            band_weight.append(((end-start)+1)/CHUNK)
            if (start_freq <= self.config.beat_min_freq and self.config.beat_min_freq <= end_freq) or \
                    (self.config.beat_min_freq <= start_freq and end_freq <= self.config.beat_max_freq) or \
                    (start_freq <= self.config.beat_max_freq and self.config.beat_max_freq <= end_freq):
                filtered_bands.append((start, end))
                filtered_indices.append(i)
                filtered_frequency.append((start_freq,end_freq))
                filtered_band_weight.append(band_weight[i])
        self.logger.info("### filtered bands")
        self.logger.info(f"bands = {filtered_bands}")
        self.logger.info(f"frequency = {filtered_frequency}")
        self.logger.info(f"indices (band number) = {filtered_indices}")
        self.logger.info(f"filtered band weight = {filtered_band_weight}")

        prev_beat = perf_counter()
        beats_empty = [0]*N_BANDS
        while True:
            beats_detected = beats_empty
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.int32).astype(np.float32)
            samples = samples.reshape(-1, CHANNELS)
            # Mean of channels
            mono_samples = np.mean(samples, axis=1)
            spectrum = np.abs(np.fft.rfft(mono_samples, n=CHUNK))

            for iband in filtered_indices:
                start, end = bands[iband]
                #band_weight = ((end - start) + 1) / CHUNK
                energy = band_weight[iband] * np.sum(spectrum[start:end] ** 2)
                energy_history[iband].append(energy)
                if energy < self.config.beat_min_energy:
                    beats_detected[iband] = 0
                    continue
    
                mean = np.mean(energy_history[iband])
                #var = np.var(energy_history[iband])
                #std = np.std(energy_history[iband])
                ratio = energy / mean
                beats_detected[iband] = (1 if ratio > self.config.beat_c_factor  else 0)
                if self.config.beat_full_debug:
                    print(f"Bande {iband:02d} | Energie: {energy_history[iband][-1]:.2e} | Moyenne: {mean:.2e} | Ratio {ratio:.2e} | Beat: {'#' if beats_detected[iband] else '-'}")      
            if sum(beats_detected) > 0:
                curr_time = time.clock_gettime(self.clk_id)
                if (curr_time - prev_beat) > self.config.beat_interval:
                    # interval between two beat in seconds (example 180BPM = 0.33s)
                    self.queue.put(("BEAT",curr_time))
                    prev_beat = curr_time
                    Thread(target=visual_beat).start()
                    
                                                                                
            if self.config.beat_debug:
                visual = ''.join(['#' if beats_detected[i] else '-' for i in range(N_BANDS)])
                print(visual)
            
            
            
