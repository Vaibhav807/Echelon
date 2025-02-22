from flask import Flask, render_template, send_file, jsonify, request
from elevenlabs.client import ElevenLabs
from elevenlabs import play, save, stream, Voice, VoiceSettings
import io
from openai import OpenAI
import threading
import pyaudio
import wave

app = Flask(__name__)
client = OpenAI(api_key="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")

# Global variables for recording
recording_thread = None
recording_active = False

def record_audio():
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                   channels=CHANNELS,
                   rate=RATE,
                   input=True,
                   frames_per_buffer=CHUNK)

    frames = []
    print("Recording started...")
    
    while recording_active:
        data = stream.read(CHUNK)
        frames.append(data)

    print("Recording stopped.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save the recorded audio
    wf = wave.open('recording.wav', 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/play-welcome')
def play_welcome():
    try:
        client = ElevenLabs(api_key="sk_3abbbf5dd2b387f328ea0cebe76bd103141bc3f30f807ad2")
        text = "Hi there, welcome to Echelon! How can I help you today?"
        audio = client.generate(
            text=text,
            voice="Chris"
        )
        play(audio)
        return jsonify({"status": "success"})
    except Exception as e:
        return str(e), 500

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_thread, recording_active
    recording_active = True
    print("Received /start_recording request.")
    recording_thread = threading.Thread(target=record_audio)
    recording_thread.start()
    return '', 204

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording_thread, recording_active
    print("Received /stop_recording request.")
    recording_active = False
    if recording_thread is not None:
        recording_thread.join()
    audio_file = 'recording.wav'
    result = transcribe_audio(audio_file)
    print(f"Final transcription: {result}")
    return result, 200

def transcribe_audio(filename='recording.wav'):
    print("Transcribing audio...")
    try:
        with open(filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        print(f"Transcription result: {transcript.text}")
        return transcript.text
    except Exception as e:
        error_message = f"Transcription error: {str(e)}"
        print(error_message)
        return error_message

if __name__ == '__main__':
    app.run(debug=True)
