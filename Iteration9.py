import ollama
import imaplib
import email
import yaml  
import openai
from openai import OpenAI

with open("details.yml") as f:
    content = f.read()
    
# from credentials.yml import user name and password
my_credentials = yaml.load(content, Loader=yaml.FullLoader)

#Load the user name, passwd, and OpenAI API key from yaml file
user = my_credentials["user"]
password = my_credentials["password"]
openai.api_key = "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"


def retrieve_emails():
    print("\n" + "="*50)
    print(f"📧 RETRIEVING ALL EMAILS FROM ALL SENDERS")
    print("="*50 + "\n")

    emails_list = []
    
    try:
        # URL for IMAP connection
        imap_url = 'imap.gmail.com'
        
        # Connection with GMAIL using SSL
        my_mail = imaplib.IMAP4_SSL(imap_url)
        
        # Log in using your credentials
        my_mail.login(user, password)
        
        # Select the Inbox to fetch messages
        my_mail.select('Inbox')
        
        # Search for ALL emails
        search_criteria = 'ALL'
        
        # Refresh connection if needed
        try:
            my_mail.noop()
        except:
            # Reconnect if connection is stale
            my_mail = imaplib.IMAP4_SSL(imap_url)
            my_mail.login(user, password)
            my_mail.select('Inbox')
        
        _, data = my_mail.search(None, search_criteria)
        
        if not data[0]:
            print("\n❌ No emails found.")
            my_mail.logout()
            return emails_list
            
        mail_id_list = data[0].split()  #IDs of all emails that we want to fetch 
        print(f"\n📬 Found {len(mail_id_list)} emails in total.\n")
        
        #Iterate through messages and extract data into the emails_list
        for num in mail_id_list:
            email_data = {}
            typ, data = my_mail.fetch(num, '(RFC822)')
            
            for response_part in data:
                if isinstance(response_part, tuple):
                    my_msg = email.message_from_bytes((response_part[1]))
                    email_data['subject'] = my_msg['subject']
                    email_data['from'] = my_msg['from']
                    email_data['date'] = my_msg['date']
                    
                    # Get email body
                    body = ""
                    for part in my_msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body += part.get_payload()
                    email_data['body'] = body
                    
                    emails_list.append(email_data)
            
        return emails_list
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return emails_list
    finally:
        try:
            my_mail.logout()
        except:
            pass

def analyze_emails(email_list, question):
    print("\n" + "="*50)
    print(f"🤖 ANALYZING EMAILS WITH GPT-4o")
    print(f"Question: {question}")
    print("="*50 + "\n")
    
    try:
        client = OpenAI(
            api_key="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"
        )
        
        # Prepare the email data for the prompt
        email_content = ""
        for idx, email in enumerate(email_list, 1):
            email_content += f"\nEmail {idx}:\n"
            email_content += f"From: {email['from']}\n"
            email_content += f"Subject: {email['subject']}\n"
            email_content += f"Date: {email['date']}\n"
            email_content += f"Body: {email['body']}\n"
            email_content += "-" * 40
        
        # Create the prompt
        prompt = f"""Here are the emails from my inbox:
{email_content}

Question: {question}

Please analyze these emails and answer the question above. Provide a clear and concise response."""

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant analyzing email content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract and return the response
        answer = response.choices[0].message.content
        print("\n📝 Analysis Result:")
        print("-" * 40)
        print(answer)
        print("-" * 40)
        
        return answer
        
    except Exception as e:
        print(f"❌ An error occurred during analysis: {str(e)}")
        return None

def analyze_emails_ollama(email_list, question):
    print("\n" + "="*50)
    print(f"🤖 ANALYZING EMAILS WITH GRANITE-3.1-DENSE-8B")
    print(f"Question: {question}")
    print("="*50 + "\n")
    
    try:
        # Prepare the email data for the prompt
        email_content = ""
        for idx, email in enumerate(email_list, 1):
            email_content += f"\nEmail {idx}:\n"
            email_content += f"From: {email['from']}\n"
            email_content += f"Subject: {email['subject']}\n"
            email_content += f"Date: {email['date']}\n"
            email_content += f"Body: {email['body']}\n"
            email_content += "-" * 40
        
        # Create the prompt
        prompt = f"""Here are the emails from my inbox:
{email_content}

Question: {question}

Please analyze these emails and answer the question above. Provide a clear and concise response."""

        # Make the Ollama API call
        response = ollama.chat(
            model='granite3.1-dense:8b',
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant analyzing email content.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        )
        
        # Extract and return the response
        answer = response['message']['content']
        print("\n📝 Granite Analysis Result:")
        print("-" * 40)
        print(answer)
        print("-" * 40)
        
        return answer
        
    except Exception as e:
        print(f"❌ An error occurred during Granite analysis: {str(e)}")
        return None

# Main loop for continuous questions
email_list = retrieve_emails()
while True:
    try:
        print("\n" + "="*50)
        question = input("\nWhat would you like to know about your emails? (type 'exit' to quit): ")
        if question.lower() == 'exit':
            print("\nGoodbye! 👋")
            break
            
        # Run both analyses
        print("\n🔄 Running analysis with both models...")
        openai_analysis = analyze_emails(email_list, question)
        ollama_analysis = analyze_emails_ollama(email_list, question)
        
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")
        break

# Example questions you could ask:
# "What are the main topics discussed in these emails?"
# "Summarize the most important emails from last week"
# "Are there any urgent action items I need to address?"
