import os
import pickle
import base64
import google.auth
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText

# Define the required OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate():
    creds = None
    # Load credentials from a token file if available
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    
    # If credentials are invalid or don't exist, authenticate via OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for future use
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    
    return creds

# Authenticate and return a Gmail API service instance
def get_gmail_service():
    creds = authenticate()
    service = build("gmail", "v1", credentials=creds)
    return service

if __name__ == "__main__":
    service = get_gmail_service()
    print("Authentication successful! You can now use the Gmail API.")
