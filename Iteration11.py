from typing import Annotated, Literal
from typing_extensions import TypedDict
import json
import imaplib
import email
import smtplib
import yaml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

# LangGraph Imports
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

# Load Credentials
with open("details.yml") as f:
    credentials = yaml.load(f, Loader=yaml.FullLoader)

user, password = credentials["user"], credentials["password"]

# Define State
class State(TypedDict):
    messages: Annotated[list, add_messages]
    email_summary: str

# Create StateGraph
graph = StateGraph(State)

# Tool: Retrieve Emails
def retrieve_emails(state: State) -> State:
    sender_email = state.get("sender_email", "default@example.com")
    start_date = state.get("start_date", "01-Jan-2025")
    end_date = state.get("end_date", "31-Jan-2025")
    
    imap_url = 'imap.gmail.com'
    try:
        mail = imaplib.IMAP4_SSL(imap_url)
        mail.login(user, password)
        mail.select('Inbox')
        search_criteria = f'(FROM "{sender_email}") SINCE "{start_date}" BEFORE "{end_date}"'
        _, data = mail.search(None, search_criteria)
        mail_ids = data[0].split()
        mail.logout()
        
        if not mail_ids:
            return {"messages": state["messages"], "email_summary": "No emails found."}
        
        return {"messages": state["messages"], "email_summary": f"Found {len(mail_ids)} emails."}
    except Exception as e:
        return {"messages": state["messages"], "email_summary": f"Error: {str(e)}"}

graph.add_node("retrieve_emails", retrieve_emails)

# Tool: Send Email
def send_email(state: State) -> State:
    recipient = state.get("recipient_email", "default@example.com")
    subject = state.get("subject", "No Subject")
    body = state.get("body", "No Body")
    
    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        
        return {"messages": state["messages"], "email_summary": "Email sent successfully!"}
    except Exception as e:
        return {"messages": state["messages"], "email_summary": f"Failed to send email: {str(e)}"}

graph.add_node("send_email", send_email)

def conditional_edge(state: State) -> Literal["send_email", "__end__"]:
    return "send_email" if "emails" in state["email_summary"] else "__end__"

graph.add_conditional_edges("retrieve_emails", conditional_edge)
graph.add_edge("send_email", "__end__")
graph.set_entry_point("retrieve_emails")

# Compile the Graph
APP = graph.compile()

# Run Example
if __name__ == "__main__":
    initial_state = {
        "messages": ["Retrieve emails and send a status update."],
        "sender_email": "vaibhav.mehra.in@gmail.com",
        "start_date": "20-Feb-2025",
        "end_date": "22-Feb-2025",
        "recipient_email": "vaibhav.mehra.in@gmail.com",
        "subject": "Project Status Update",
        "body": "Hi team, Here is the weekly project status update. Best regards, AI Assistant."
    }
    final_state = APP.invoke(initial_state)
    print(final_state["email_summary"])
    