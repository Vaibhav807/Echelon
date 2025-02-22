from flask import Flask, render_template, request, jsonify, Response
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import pyaudio
import wave
import threading
import yaml
import imaplib
import email
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import ollama
from ollama import chat
from openai import OpenAI

app = Flask(__name__)

# ------------------------------
# Configure your OpenAI for ASR
# ------------------------------
client = OpenAI(api_key="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")

# ------------------------------
# Load Credentials
# ------------------------------
with open("details.yml") as f:
    content = f.read()
my_credentials = yaml.load(content, Loader=yaml.FullLoader)
user, password = my_credentials["user"], my_credentials["password"]

# ------------------------------
# Global Vars for Recording
# ------------------------------
recording_thread = None
recording_active = False

# We'll store the latest transcription in a global so SSE route can access it
latest_transcription = ""

# ---------------------------------------------------------------------
# Recording Audio
# ---------------------------------------------------------------------
def record_audio():
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100

    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    frames = []
    print("Recording started...")
    
    while recording_active:
        data = stream.read(CHUNK)
        frames.append(data)

    print("Recording stopped.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open('recording.wav', 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

# ---------------------------------------------------------------------
# Transcription Utility
# ---------------------------------------------------------------------
def transcribe_audio(filename='recording.wav'):
    print("Transcribing audio with OpenAI Whisper...")
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

# ---------------------------------------------------------------------
# Text-to-Speech Utility
# ---------------------------------------------------------------------
def text_to_speech(text: str) -> str:
    """
    Convert text to speech using ElevenLabs, then play it.
    """
    try:
        print("Invoking ElevenLabs TTS...")
        tts_client = ElevenLabs(api_key="sk_a199ae8b51f9afd556a30b3e3a4b33caf653f73e3d726ee3")
        audio = tts_client.generate(text=text, voice="Chris")
        play(audio)
    except Exception as e:
        print(f"Error in text_to_speech: {str(e)}")
        return ""
    return ""

# ---------------------------------------------------------------------
# Flask Routes
# ---------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index1.html')

@app.route('/play-welcome')
def play_welcome():
    try:
        print("Playing welcome message...")
        text_to_speech("Hey, it's Echelon! What can I do for you today?")
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
    """
    Stop recording and transcribe the audio. 
    If user said "summarize", we handle that in the SSE route afterwards.
    """
    global recording_thread, recording_active, latest_transcription
    print("Received /stop_recording request.")
    recording_active = False
    if recording_thread is not None:
        recording_thread.join()

    audio_file = 'recording.wav'
    result = transcribe_audio(audio_file)
    latest_transcription = result  # Store in global for SSE route

    print(f"Final transcription: {result}")
    return result, 200

@app.route('/auto_summarize', methods=['GET'])
def auto_summarize():
    """
    SSE route with minimal yields:
      - "Thinking..."
      - "Retrieving emails from {current_date}..."
      - "Summarizing..."
      - "Presenting summary..."
      - "Task complete!"
      - "Done" (to close SSE)
    """
    def generate():
        global latest_transcription
        transcript = latest_transcription.strip()

        # If user did not request summarization, quietly close SSE.
        if "summarize" not in transcript.lower():
            yield "data: Done\n\n"
            return

        # 1) Thinking...
        yield "data: Thinking...\n\n"
        print("Thinking started (TTS).")
        try:
            text_to_speech("Sure, no problem, I will summarize the new emails you have received today.")
        except Exception as e:
            print("TTS error:", e)

        # 2) Retrieving emails
        current_date = datetime.now().strftime("%d-%b-%Y")
        yield f"data: Retrieving emails from {current_date}...\n\n"
        print("Retrieving emails from", current_date)

        imap_url = 'imap.gmail.com'
        try:
            my_mail = imaplib.IMAP4_SSL(imap_url)
            my_mail.login(user, password)
            my_mail.select('Inbox')
        except Exception as e:
            print("IMAP error:", e)
            yield "data: Done\n\n"
            return

        try:
            my_mail.noop()
        except:
            my_mail = imaplib.IMAP4_SSL(imap_url)
            my_mail.login(user, password)
            my_mail.select('Inbox')

        search_criteria = f'SINCE "{current_date}"'
        _, data = my_mail.search(None, search_criteria)
        if not data[0]:
            yield "data: Task complete\n\n"
            yield "data: Done\n\n"
            my_mail.logout()
            return

        mail_id_list = data[0].split()
        msgs = []
        email_details = []
        for num in mail_id_list:
            typ, email_data = my_mail.fetch(num, '(RFC822)')
            msgs.append(email_data)

        for msg in msgs[::-1]:
            for response_part in msg:
                if isinstance(response_part, tuple):
                    my_msg = email.message_from_bytes(response_part[1])
                    subject = my_msg['subject']
                    sender_email = my_msg['from']
                    body = ""
                    for part in my_msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body = part.get_payload(decode=True).decode()
                    email_details.append({
                        'subject': subject,
                        'sender': sender_email,
                        'body': body
                    })

        # 3) Summarizing...
        yield "data: Summarizing...\n\n"
        print("Summarizing with Ollama")

        if not email_details:
            yield "data: Task complete\n\n"
            yield "data: Done\n\n"
            my_mail.logout()
            return

        combined_details = ""
        for ed in email_details:
            combined_details += (
                f"Subject: {ed['subject']}\n"
                f"From: {ed['sender']}\n"
                f"Body:\n{ed['body']}\n\n"
            )

        system_prompt = (
            "You are Echelon, my personal assistant. "
            "Your sole task is to summarize all the emails below in no more than three sentences. "
            "Please speak in a conversational tone."
        )
        try:
            response = chat(
                model='granite3.1-dense:8b',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': combined_details}
                ]
            )
            summary = response['message']['content']
            print("Summarization complete\n", summary)
            my_mail.logout()
        except Exception as e:
            print("Summarization error:", e)
            my_mail.logout()
            yield "data: Done\n\n"
            return

        # 4) Presenting summary...
        yield "data: Presenting summary...\n\n"
        text_to_speech(summary)

        # 5) Task complete!
        yield "data: Task complete!\n\n"
        yield "data: Done\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)
