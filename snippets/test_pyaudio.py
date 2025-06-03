import numpy as np
import pyaudio
import wave

DEVICE_NAME = "ADCWM8782"
p = pyaudio.PyAudio()
chunk = 1024
sample_format = pyaudio.paInt32
channels = 2
fs = 96000
filename = "output.wav"
seconds = 20

def find_input_device(name_part="Loopback"):
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if name_part.lower() in info['name'].lower() and info['maxInputChannels'] > 0:
            return i
    return None

device_index = find_input_device(DEVICE_NAME)

stream = p.open(format = sample_format, channels = channels, rate = fs, input=True,
                input_device_index=device_index, frames_per_buffer = chunk)
frames = []
# store date in chunks for n seconds
for i in range(0, int(fs/chunk * seconds)):
    data = stream.read(chunk)
    frames.append(data)

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open(filename, 'wb')
wf.setnchannels(channels)
wf.setsampwidth(p.get_sample_size(sample_format))
wf.setframerate(fs)
wf.writeframes(b''.join(frames))
wf.close()

