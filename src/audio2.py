import pyaudio, wave, utils

BUFFER_SIZE = 1024
REC_SECONDS = 5
RATE = 44100
WAV_FILENAME = utils.generate_random_token()
FORMAT = pyaudio.paInt16

#init sound stream
pa = pyaudio.PyAudio()
stream = pa.open(
    format = FORMAT,
    input = True,
    channels = 1,
    rate = RATE,
    input_device_index = 7,
    frames_per_buffer = BUFFER_SIZE
)

#run recording
print('Recording...')
data_frames = []
for f in range(0, RATE/BUFFER_SIZE * REC_SECONDS):
    data = stream.read(BUFFER_SIZE)
    data_frames.append(data)
print('Finished recording...')
stream.stop_stream()
stream.close()
pa.terminate()
