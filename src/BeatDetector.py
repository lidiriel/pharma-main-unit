import threading
import logging
import time
import Pins
import pyaudio
from collections import deque
from time import perf_counter
import numpy as np
import minimalmodbus
import json
import random

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

class BeatDetector(threading.Thread):
    def __init__(self, config, queue):
        super().__init__()
        self.config = config
        self.queue = queue
        self.pa = pyaudio.PyAudio()
        self.logger = logging.getLogger('BeatDetector')
        self.logger.setLevel(logging.INFO)
        
        self.instrument = minimalmodbus.Instrument(port='/dev/ttyAMA0', slaveaddress=0)
        self.instrument.serial.baudrate = config.com_serial_baudrate
        self.instrument.serial.bytesize = 8
        self.instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
        self.instrument.serial.stopbits = 1
        self.instrument.serial.timeout = 0
        self.instrument.mode = minimalmodbus.MODE_RTU
        self.instrument.clear_buffers_before_each_transaction = True
        
        self.clk_id = time.CLOCK_REALTIME
    
    
    def find_input_device(self, name="Loopback"):
        self.logger.info(f"search for device {name}")
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            self.logger.debug(f"device {i} info {info['name']}")
            if name.lower() in info['name'].lower() and info['maxInputChannels'] > 0:
                return i
        return None
        
    # === Distribution logarithmique des fréquences ===
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
    
    def send_pattern(self, tick):
        try:
            element = self.sequence[self.sequence_idx]
            code = 0
            if element == "RAND":
                code = random.randint(0,255)
                # duplicate code for two cross
                code = (code << 8) | code
            else:
                code = int(element,0)
            self.instrument.write_register(REGISTER_LED, code)
            my_time = time.clock_gettime(self.clk_id) - tick
            self.logger.info(f"sended code {code:#04x} sending latency {my_time}")
            self.sequence_idx = (self.sequence_idx + 1) % self.sequence_len
        except Exception as e:
            self.logger.error(f"Send pattern error {e}")
        
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
        
        self.logger.info(f"Set sequence to {SEQ_NAME}")
        self.sequence = data[SEQ_NAME]
        self.sequence_idx = 0
        self.sequence_len = len(self.sequence) 
        
        device_index = self.find_input_device(name=self.config.beat_device_name)
        if device_index is None:
            self.logger.error("Périphérique d'entrée non trouvé.")
            raise RuntimeError("Périphérique d'entrée non trouvé.")


        stream = self.pa.open(format=SAMPLE_FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK)

        # === Historique énergie pour chaque bande ===
        energy_history = [deque(maxlen=ENERGY_HISTORY) for _ in range(N_BANDS)]

        bands = self.log_frequency_bands()
        self.logger.debug(f"bands = {bands}")
        
        # Band filtering according to frequency
        def band_to_freq(index):
            return index * RATE / CHUNK
        
        filtered_bands = []
        filtered_indices = []
        filtered_frequency = []
        for i, (start, end) in enumerate(bands):
            start_freq = band_to_freq(start)
            end_freq = band_to_freq(end)
            if (start_freq <= self.config.beat_min_freq and self.config.beat_min_freq <= end_freq) or \
                    (self.config.beat_min_freq <= start_freq and end_freq <= self.config.beat_max_freq) or \
                    (start_freq <= self.config.beat_max_freq and self.config.beat_max_freq <= end_freq):
                filtered_bands.append((start, end))
                filtered_indices.append(i)
                filtered_frequency.append((start_freq,end_freq))
        self.logger.debug("### filtered bands")
        self.logger.debug(f"bands = {filtered_bands}")
        self.logger.debug(f"frequency = {filtered_frequency}")
        self.logger.debug(f"indices (band number) = {filtered_indices}")

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
                band_weight = ((end - start) + 1) / CHUNK
                energy = band_weight * np.sum(spectrum[start:end] ** 2)
                energy_history[iband].append(energy)
                if energy < self.config.beat_min_energy:
                    beats_detected[iband] = 0
                    continue
    
                mean = np.mean(energy_history[iband])
                #var = np.var(energy_history[iband])
                #std = np.std(energy_history[iband])
                ratio = energy / mean
                beats_detected[iband] = (1 if ratio > self.config.beat_c_factor  else 0)
                if self.config.beat_debug:
                    #print(energy_history[iband])
                    #print(f"Bande {iband:02d} | Energie: {energy_history[iband][-1]:.2e} | Moyenne: {mean:.2e} | Ratio {ratio:.2e} | Std: {std:.2e} | Var: {var:.2e} | Beat: {'#' if beats_detected[iband] else '-'}")
                    pass       
            if sum(beats_detected) >= 1:
                curr_time = time.clock_gettime(self.clk_id)
                if (curr_time - prev_beat) > self.config.beat_interval:
                    # < 180 BPM max
                    self.send_pattern(tick = curr_time)
                    prev_beat = curr_time
                    #self.queue.put(("BEAT",curr_time))
                else:
                    # > 180 BPM
                    beats_detected = beats_empty
                                                                                
            if self.config.beat_debug:
                visual = ''.join(['#' if beats_detected[i] else '-' for i in range(N_BANDS)])
                print(visual)
            #time.sleep(0.03)
            
            
            
