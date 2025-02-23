from flask import Flask, render_template, request, jsonify, Response
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import pyaudio
import wave
import threading
import yaml
import time
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

# -------------------------------------------------
# Configure your OpenAI for ASR
# -------------------------------------------------
client = OpenAI(api_key=(
    "sk-proj-jqG-7FG_VN6QbyJ55-2wOn1dcQpoKekkecvOszYeQyxp7JFGM"
    "-Wb100dEgbR90gQQbxeCOKelMT3BlbkFJhfrWd9ibzgLJ82YHcmnWpz7gOl"
    "1K07gY0TS7YW1afa-NAUHedfmuzkTQa5Uh5wWwm6QyhhDMMA"
))

# -------------------------------------------------
# Load Credentials
# -------------------------------------------------
with open("details.yml") as f:
    content = f.read()
my_credentials = yaml.load(content, Loader=yaml.FullLoader)
user, password = my_credentials["user"], my_credentials["password"]

# -------------------------------------------------
# Global Vars
# -------------------------------------------------
recording_thread = None
recording_active = False
latest_transcription = ""

# -------------------------------------------------
# Recording Audio
# -------------------------------------------------
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

# -------------------------------------------------
# Transcription Utility
# -------------------------------------------------
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

# -------------------------------------------------
# Text-to-Speech Utility
# -------------------------------------------------
def text_to_speech(text: str) -> str:
    """Convert text to speech using ElevenLabs, then play it."""
    try:
        print("Invoking ElevenLabs TTS...")
        tts_client = ElevenLabs(api_key="sk_a199ae8b51f9afd556a30b3e3a4b33caf653f73e3d726ee3")
        audio = tts_client.generate(text=text, voice="Chris")
        play(audio)
    except Exception as e:
        print(f"Error in text_to_speech: {str(e)}")
        return ""
    return ""

# -------------------------------------------------
# Summarization Logic (unchanged)
# -------------------------------------------------
def summarize_emails():
    """
    The existing function for summarizing emails, with
    yield statements that must remain unchanged.
    """
    yield "data: Thinking...\n\n"
    print("Thinking started (TTS).")
    try:
        text_to_speech("Sure, no problem, I will summarize the new emails you have received today??")
    except Exception as e:
        print("TTS error:", e)

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

    yield "data: Presenting summary...\n\n"
    text_to_speech(summary)
    yield "data: Task complete!\n\n"
    yield "data: Done\n\n"

# -------------------------------------------------
# Combined function to handle "low" priority
# with minimal yields
# -------------------------------------------------
def handle_low_emails(user, password):
    print("\n========== STARTING HANDLE_LOW_EMAILS ==========")
    print(f"Current user: {user}")
    
    yield "data: Processing your request\n\n"
    text_to_speech("Certainly, I will process your request to identify low priority emails. Please give me a moment.")
    print("Starting handle_low_emails... YIELD")

    current_date = datetime.now().strftime("%d-%b-%Y")
    print(f"Checking emails from {current_date}... YIELD")

    try:
        print("Attempting IMAP connection...")
        imap_url = 'imap.gmail.com'
        my_mail = imaplib.IMAP4_SSL(imap_url)
        print("IMAP connection successful")
        
        print("Attempting login...")
        my_mail.login(user, password)
        print("Login successful")
        
        print("Selecting inbox...")
        my_mail.select('Inbox')
        print("Inbox selected")

        search_criteria = f'SINCE "{current_date}"'
        print(f"Searching with criteria: {search_criteria}")
        _, data = my_mail.search(None, search_criteria)
        yield "data: Identifying all suitable emails\n\n"
        if not data[0]:
            yield "data: No low emails found.\n\n"
            print("No low emails found. YIELD")
            yield "data: Done\n\n"
            print("Done YIELD")
            my_mail.logout()
            return

        mail_id_list = data[0].split()
        print(f"Found {len(mail_id_list)} total emails")
        msgs = []
        email_details = []

        print("\n----- Starting email fetch loop -----")
        for num in mail_id_list:
            print(f"Fetching email ID: {num}")
            typ, raw_data = my_mail.fetch(num, '(RFC822)')
            msgs.append(raw_data)
        print(f"Fetched {len(msgs)} messages")

        print("\n----- Processing email contents -----")
        for i, msg in enumerate(msgs[::-1]):
            print(f"Processing message {i+1}/{len(msgs)}")
            for response_part in msg:
                if isinstance(response_part, tuple):
                    my_msg = email.message_from_bytes(response_part[1])
                    subject = my_msg['subject']
                    sender_email = my_msg['from']
                    print(f"Found email - Subject: {subject[:30]}... | From: {sender_email}")
                    
                    body = ""
                    for part in my_msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body = part.get_payload(decode=True).decode()
                    email_details.append({
                        'subject': subject,
                        'sender': sender_email,
                        'body': body
                    })

        if not email_details:
            yield "data: No email details found.\n\n"
            print("No email details found. YIELD")
            yield "data: Done\n\n"
            print("Done YIELD")
            my_mail.logout()
            return

        print("\n----- Preparing GPT request -----")
        combined = ""
        for i, ed in enumerate(email_details):
            print(f"Adding email {i} to combined text")
            combined += (
                f"Email:{i}\nSubject:{ed['subject']}\nFrom:{ed['sender']}\nBody:{ed['body']}\n\n"
            )

        yield "data: Sorting emails by importance\n\n"
        print("Sorting emails by importance... YIELD")
        print("\n----- Calling GPT for importance sorting -----")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                'role': 'system',
                'content': f"""
                You are an AI. Sort these emails by importance in the format: 0,1,2
                {combined}
                """
            }]
        )
        order_str = response.choices[0].message.content
        print(f"GPT returned order: {order_str}")
        
        idx_list = [int(x) for x in order_str.split(',')]
        print(f"Parsed indices: {idx_list}")
        
        sorted_list = [email_details[i] for i in idx_list]
        print(f"Successfully sorted {len(sorted_list)} emails")
        my_mail.logout()
        print("IMAP logout successful")

        if len(sorted_list) < 2:
            yield "data: Not enough emails to have 'low' emails.\n\n"
            print("Not enough emails to have 'low' emails. YIELD")
            yield "data: Done\n\n"
            print("Done YIELD")
            return

        high_email = sorted_list[0]
        low_emails = sorted_list[1:]
        print(f"\n----- Processing low priority emails -----")
        print(f"High priority email subject: {high_email['subject'][:30]}...")
        print(f"Found {len(low_emails)} low priority emails")

        yield f"data: Found {len(low_emails)} low-priority emails, sending...\n\n"
        print(f"Found {len(low_emails)} low-priority emails, sending... YIELD")

        print("\n----- Starting SMTP processing -----")
        for i, ed in enumerate(low_emails):
            print(f"\nProcessing low priority email {i+1}/{len(low_emails)}")
            print(f"From: {ed.get('sender','???')}")
            yield f"data: Processing email {i+1} of {len(low_emails)}\n\n"
            print(f"Processing email from {ed.get('sender','???')} YIELD")

            try:
                print("Generating GPT reply...")
                gpt_resp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        'role': 'system',
                        'content': f"""
                        You are Vaibhav's AI assistant. 
                        Based on email with subject: {ed['subject']} 
                        from {ed['sender']}, body: {ed['body']},
                        generate a reply in format:
                        Recipient_email: ...
                        Subject: ...
                        Body: ...
                        """
                    }]
                )
                gen_text = gpt_resp.choices[0].message.content
                print("GPT reply generated successfully")
                yield f"data: Generating reply for email {i+1} of {len(low_emails)}\n\n"
                print(f"Generated GPT reply:\n{gen_text} YIELD")

                print("Parsing generated content...")
                rec, subj, new_body = parse_generated_content(gen_text)
                if not rec:
                    print(f"Failed to parse recipient for {ed['sender']}")
                    yield f"data: No recipient found for {ed['sender']}\n\n"
                    continue
                print(f"Parsed content - Recipient: {rec} | Subject: {subj}")

                print("Preparing MIME message...")
                msg = MIMEMultipart()
                msg['From'] = user
                msg['To'] = rec
                msg['Subject'] = subj
                msg.attach(MIMEText(new_body, 'plain'))

                try:
                    print("Attempting SMTP connection...")
                    server = smtplib.SMTP("smtp.gmail.com", 587)
                    server.starttls()
                    print("SMTP TLS started")
                    
                    print("Attempting SMTP login...")
                    server.login(user, password)
                    print("SMTP login successful")
                    
                    print(f"Sending email to {rec}...")
                    server.send_message(msg)
                    print("Email sent successfully")
                    
                    server.quit()
                    print("SMTP connection closed")
                    yield f"data: ✅ Email {i+1} of {len(low_emails)} has been sent\n\n"
                    print(f"✅ Sent to {rec} YIELD")
                except Exception as e:
                    print(f"SMTP Error: {str(e)}")
                    yield f"data: ❌ Error sending to {rec}: {str(e)}\n\n"

            except Exception as e:
                print(f"GPT Processing Error: {str(e)}")
                yield f"data: ❌ GPT error: {str(e)}\n\n"
                print(f"❌ GPT error: {str(e)} YIELD")

        print("\n========== COMPLETED HANDLE_LOW_EMAILS ==========")
        yield "data: Task completed successfully\n\n"
        text_to_speech("All low priority emails have been processed and their respective replies have been sent.")
        print("Done with low-priority emails. YIELD")
        
        yield "data: Done\n\n"
        print("Done YIELD")

    except Exception as e:
        print(f"\nFATAL ERROR in handle_low_emails: {str(e)}")
        yield f"data: ❌ Error: {str(e)}\n\n"
        print(f"❌ Error: {str(e)} YIELD")
        yield "data: Done\n\n"
        print("Done YIELD")

# -------------------------------------------------
# ONLY THIS FUNCTION CHANGED
# -------------------------------------------------
def handle_high_emails(user, password):
    print("\n========== STARTING HANDLE_HIGH_EMAILS ==========")
    print(f"Current user: {user}")

    yield "data: Processing your request\n\n"
    print("Initial yield sent")

    current_date = datetime.now().strftime("%d-%b-%Y")
    print(f"Processing emails from date: {current_date}")

    try:
        print("\n----- IMAP Connection Setup -----")
        print("Attempting IMAP connection...")
        imap_url = 'imap.gmail.com'
        my_mail = imaplib.IMAP4_SSL(imap_url)
        print("IMAP connection successful")
        
        print("Attempting login...")
        my_mail.login(user, password)
        print("Login successful")
        
        print("Selecting inbox...")
        my_mail.select('Inbox')
        print("Inbox selected")

        search_criteria = f'SINCE "{current_date}"'
        print(f"Searching with criteria: {search_criteria}")
        _, data = my_mail.search(None, search_criteria)
        
        if not data[0]:
            print("No emails found for today")
            yield "data: No emails found today.\n\n"
            yield "data: Done\n\n"
            my_mail.logout()
            return

        mail_id_list = data[0].split()
        print(f"Found {len(mail_id_list)} total emails")
        msgs = []
        email_details = []

        print("\n----- Starting email fetch loop -----")
        for num in mail_id_list:
            print(f"Fetching email ID: {num}")
            typ, raw_data = my_mail.fetch(num, '(RFC822)')
            msgs.append(raw_data)
        print(f"Fetched {len(msgs)} messages")

        print("\n----- Processing email contents -----")
        for i, msg in enumerate(msgs[::-1]):
            print(f"Processing message {i+1}/{len(msgs)}")
            for response_part in msg:
                if isinstance(response_part, tuple):
                    my_msg = email.message_from_bytes(response_part[1])
                    subject = my_msg['subject']
                    sender_email = my_msg['from']
                    print(f"Found email - Subject: {subject[:30]}... | From: {sender_email}")
                    
                    body = ""
                    for part in my_msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body = part.get_payload(decode=True).decode()
                    email_details.append({
                        'subject': subject,
                        'sender': sender_email,
                        'body': body
                    })

        if not email_details:
            print("No email details found after processing")
            yield "data: No email details found.\n\n"
            yield "data: Done\n\n"
            my_mail.logout()
            return

        print("\n----- Preparing GPT request -----")
        combined = ""
        for i, ed in enumerate(email_details):
            print(f"Adding email {i} to combined text")
            combined += (
                f"Email:{i}\nSubject:{ed['subject']}\nFrom:{ed['sender']}\nBody:{ed['body']}\n\n"
            )

        print("\n----- Calling GPT for importance sorting -----")
        yield "data: Sorting emails by importance...\n\n"
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                'role': 'system',
                'content': f"""
                You are an AI. Sort these emails by importance, e.g. '0,2,1':
                {combined}
                """
            }]
        )
        order_str = resp.choices[0].message.content
        print(f"GPT returned order: {order_str}")
        
        idx_list = [int(x) for x in order_str.split(',')]
        print(f"Parsed indices: {idx_list}")
        
        sorted_list = [email_details[i] for i in idx_list]
        print(f"Successfully sorted {len(sorted_list)} emails")
        my_mail.logout()
        print("IMAP logout successful")

        if not sorted_list:
            print("No sorted emails found")
            yield "data: Could not find any sorted emails.\n\n"
            yield "data: Done\n\n"
            return

        high_email = sorted_list[0]
        print(f"\n----- Processing highest priority email -----")
        print(f"High priority email subject: {high_email['subject'][:30]}...")
        print(f"High priority email from: {high_email['sender']}")
        yield f"data: Found 1 high-priority email from {high_email['sender']}.\n\n"

        # ---------------
        # MULTI-ITERATION GPT LOOP WITH CONSOLE FEEDBACK
        # ---------------
        max_iterations = 10
        iteration = 0
        final_draft = ""
        feedback = ""

        while iteration < max_iterations:
            if iteration == 0:
                prompt_text = f"""
                You are Vaibhav's AI assistant.
                Based on this high-priority email:
                  Subject: {high_email['subject']}
                  From: {high_email['sender']}
                  Body: {high_email['body']}

                Generate a draft reply in the following format:
                  Recipient_email: ...
                  Subject: ...
                  Body: ...
                """
            else:
                prompt_text = f"""
                You are Vaibhav's AI assistant.
                Here is the previous draft:
                {final_draft}
                and the user requested improvements.
                {feedback}

                The user requested improvements.
                Please generate an improved draft in the same format:
                  Recipient_email: ...
                  Subject: ...
                  Body: ...
                """

            print(f"\n----- GPT iteration {iteration+1} -----")
            gpt_resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{'role': 'system', 'content': prompt_text}]
            )
            draft = gpt_resp.choices[0].message.content.strip()
            final_draft = draft

            # Extract only the email body (after the "Body:" label)
            if "Body:" in draft:
                body_text = draft.split("Body:", 1)[1].strip()
            else:
                body_text = draft.strip()

            # Build an SSE message that preserves multiple lines.
            draft_lines = body_text.splitlines()
            if draft_lines:
                sse_message = "data: DRAFT_CONTENT:" + draft_lines[0]
                for line in draft_lines[1:]:
                    sse_message += "\n" + "data: " + line
                sse_message += "\n\n"
            else:
                sse_message = "data: DRAFT_CONTENT:\n\n"

            yield sse_message
            print("GPT reply draft (body only):\n", body_text)

            # --- Modified feedback block: integrated inline voice feedback using Whisper ---
            yield "data: Please provide voice feedback via voice input. Press the 'v' key to start recording, then press 'v' again to stop recording.\n\n"
            print("Please provide voice feedback: Press 'v' to start, then 'v' again to stop recording.")
            import sys
            if sys.platform == 'win32':
                import msvcrt
                print("Using Windows input method for voice feedback.")
                # Wait for 'v' key press to start recording
                print("Press 'v' to start recording feedback.")
                while True:
                    ch = msvcrt.getch()
                    if ch == b'v':
                        break
                # Inline recording using local variables
                CHUNK = 1024
                FORMAT = pyaudio.paInt16
                CHANNELS = 1
                RATE = 44100
                p_feedback = pyaudio.PyAudio()
                stream_feedback = p_feedback.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
                frames_feedback = []
                print("Recording feedback... Press 'v' again to stop recording.")
                while True:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        if ch == b'v':
                            break
                    data = stream_feedback.read(CHUNK)
                    frames_feedback.append(data)
                print("Feedback recording stopped.")
                stream_feedback.stop_stream()
                stream_feedback.close()
                p_feedback.terminate()
                wf_feedback = wave.open('feedback_recording.wav', 'wb')
                wf_feedback.setnchannels(CHANNELS)
                wf_feedback.setsampwidth(p_feedback.get_sample_size(FORMAT))
                wf_feedback.setframerate(RATE)
                wf_feedback.writeframes(b''.join(frames_feedback))
                wf_feedback.close()
                feedback = transcribe_audio("feedback_recording.wav").strip().lower()
                print("Voice feedback received:", feedback)
            else:
                import termios, tty
                print("Using Unix input method for voice feedback.")
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setraw(sys.stdin.fileno())
                    print("Press 'v' to start recording feedback.")
                    ch = sys.stdin.read(1)
                    while ch != "v":
                        ch = sys.stdin.read(1)
                    # Inline recording using local variables
                    CHUNK = 1024
                    FORMAT = pyaudio.paInt16
                    CHANNELS = 1
                    RATE = 44100
                    p_feedback = pyaudio.PyAudio()
                    stream_feedback = p_feedback.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
                    frames_feedback = []
                    print("Recording feedback... Press 'v' again to stop recording.")
                    while True:
                        ch = sys.stdin.read(1)
                        if ch == "v":
                            break
                        data = stream_feedback.read(CHUNK)
                        frames_feedback.append(data)
                    print("Feedback recording stopped.")
                    stream_feedback.stop_stream()
                    stream_feedback.close()
                    p_feedback.terminate()
                    wf_feedback = wave.open('feedback_recording.wav', 'wb')
                    wf_feedback.setnchannels(CHANNELS)
                    wf_feedback.setsampwidth(p_feedback.get_sample_size(FORMAT))
                    wf_feedback.setframerate(RATE)
                    wf_feedback.writeframes(b''.join(frames_feedback))
                    wf_feedback.close()
                    feedback = transcribe_audio("feedback_recording.wav").strip().lower()
                    print("Voice feedback received:", feedback)
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            # --- End modified feedback block ---

            if "satisfied" in feedback:
                print("User is satisfied. Finalizing...")
                break
            else:
                print("User requested improvement. Generating next iteration...")
                iteration += 1

        # ---------------
        # PARSE FINAL DRAFT & SEND EMAIL
        # ---------------
        lines = final_draft.split('\n')
        if len(lines) < 2:
            yield "data: Could not parse final draft.\n\n"
            yield "data: Done\n\n"
            return

        rec_line = lines[0].split(':', 1)
        sub_line = lines[1].split(':', 1)
        if len(rec_line) < 2 or len(sub_line) < 2:
            yield "data: Invalid final GPT format.\n\n"
            yield "data: Done\n\n"
            return

        recipient = rec_line[-1].strip()
        new_subject = sub_line[-1].strip()
        new_body = '\n'.join(lines[2:]).strip()

        print(f"\n----- Final parse -> To: {recipient}, Subject: {new_subject} -----")
        yield f"data: Sending high-priority email to {recipient}\n\n"

        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = recipient
        msg['Subject'] = new_subject
        msg.attach(MIMEText(new_body, 'plain'))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            print("SMTP TLS started")
            
            server.login(user, password)
            print("SMTP login successful")
            
            server.send_message(msg)
            print("Email sent successfully")

            server.quit()
            print("SMTP connection closed")
            yield f"data: ✅ Email sent to {recipient}\n\n"

        except Exception as e:
            print(f"Error sending high-priority email: {str(e)}")
            yield f"data: ❌ Error sending email: {str(e)}\n\n"

        print("\n========== COMPLETED HANDLE_HIGH_EMAILS ==========")
        yield "data: Done\n\n"

    except Exception as e:
        print(f"\nFATAL ERROR in handle_high_emails: {str(e)}")
        yield f"data: ❌ Error in handle_high_emails: {str(e)}\n\n"
        yield "data: Done\n\n"


# -------------------------------------------------
# Routes
# -------------------------------------------------
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
    global recording_thread, recording_active, latest_transcription
    print("Received /stop_recording request.")
    recording_active = False
    if recording_thread is not None:
        recording_thread.join()

    audio_file = 'recording.wav'
    result = transcribe_audio(audio_file)
    latest_transcription = result
    print(f"Final transcription: {result}")
    return result, 200

@app.route('/auto_summarize', methods=['GET'])
def auto_summarize():
    """
    SSE route:
      - if "summarize", call summarize_emails
      - if "low", call handle_low_emails
      - if "high", you can do something else
      - else done
    """
    def generate():
        transcript = latest_transcription.strip().lower()

        if "summarize" in transcript:
            yield from summarize_emails()

        elif "low" in transcript:
            yield from handle_low_emails(user, password)

        elif "high" in transcript:
            yield from handle_high_emails(user, password)

    return Response(generate(), mimetype='text/event-stream')

def parse_generated_content(generated_content):
    """Simple parser for GPT output with minimal error handling."""
    try:
        lines = generated_content.strip().split('\n')
        rec = lines[0].split(':', 1)[-1].strip()
        subj = lines[1].split(':', 1)[-1].strip()
        body = '\n'.join(lines[2:]).strip()
        return rec, subj, body
    except:
        return None, None, None

if __name__ == '__main__':
    app.run(debug=True)
