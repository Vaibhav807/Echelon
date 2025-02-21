import ollama
import imaplib
import email

import yaml  #To load saved login credentials from a yaml file

with open("details.yml") as f:
    content = f.read()
    
# from credentials.yml import user name and password
my_credentials = yaml.load(content, Loader=yaml.FullLoader)

#Load the user name and passwd from yaml file
user, password = my_credentials["user"], my_credentials["password"]

def retrieve_emails(sender_email, start_date, end_date):

    try:
        # URL for IMAP connection
        imap_url = 'imap.gmail.com'
        
        # Connection with GMAIL using SSL
        my_mail = imaplib.IMAP4_SSL(imap_url)
        
        # Log in using your credentials
        my_mail.login(user, password)
        
        # Select the Inbox to fetch messages
        my_mail.select('Inbox')
        
        # Combine search criteria for date range
        search_criteria = f'(FROM "{sender_email}") SINCE "{start_date}" BEFORE "{end_date}"'
        
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
            print("No emails found matching the criteria.")
            my_mail.logout()
            return
            
        mail_id_list = data[0].split()  #IDs of all emails that we want to fetch 
        
        msgs = [] # empty list to capture all messages
        #Iterate through messages and extract data into the msgs list
        for num in mail_id_list:
            typ, data = my_mail.fetch(num, '(RFC822)')
            msgs.append(data)
            
        #Print the messages
        for msg in msgs[::-1]:
            for response_part in msg:
                if type(response_part) is tuple:
                    my_msg=email.message_from_bytes((response_part[1]))
                    print("_________________________________________")
                    print ("subj:", my_msg['subject'])
                    print ("from:", my_msg['from'])
                    print ("body:")
                    for part in my_msg.walk():  
                        if part.get_content_type() == 'text/plain':
                            print (part.get_payload())
                            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        try:
            my_mail.logout()
        except:
            pass

def send_email(recipient_email, subject, body, attachments=None):
    """
    Send an email using Gmail SMTP server
    
    Parameters:
    recipient_email (str): Email address of the recipient
    subject (str): Subject of the email
    body (str): Body content of the email
    attachments (list): Optional list of file paths to attach
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication
    import os

    # Create the MIME object
    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Add body to email
    msg.attach(MIMEText(body, 'plain'))

    # Add attachments if any
    if attachments:
        for file_path in attachments:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    attachment = MIMEApplication(f.read(), _subtype=os.path.splitext(file_path)[1][1:])
                    attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))
                    msg.attach(attachment)

    try:
        # Create SMTP session
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS
        
        # Login using the same credentials from your YAML file
        server.login(user, password)
        
        # Send email
        server.send_message(msg)
        print("Email sent successfully!")
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        
    finally:
        try:
            server.quit()
        except:
            pass

class MasterLLM:
    def __init__(self):
        print("\n=== Initializing MasterLLM ===")
        # Load credentials directly in init
        with open("details.yml") as f:
            content = f.read()
        my_credentials = yaml.load(content, Loader=yaml.FullLoader)
        self.user = my_credentials["user"]
        self.password = my_credentials["password"]
        self.available_tools = {
            'retrieve_emails': self.retrieve_emails,
            'send_email': self.send_email
        }
        print("MasterLLM initialized with email tools\n")

    def retrieve_emails(self, sender_email, start_date, end_date):
        print(f"\n=== Retrieving emails from {sender_email} [{start_date} to {end_date}] ===")
        try:
            # URL for IMAP connection
            imap_url = 'imap.gmail.com'
            
            # Connection with GMAIL using SSL
            my_mail = imaplib.IMAP4_SSL(imap_url)
            
            # Log in using your credentials
            my_mail.login(self.user, self.password)
            
            # Select the Inbox to fetch messages
            my_mail.select('Inbox')
            
            # Combine search criteria for date range
            search_criteria = f'(FROM "{sender_email}") SINCE "{start_date}" BEFORE "{end_date}"'
            
            # Refresh connection if needed
            try:
                my_mail.noop()
            except:
                # Reconnect if connection is stale
                my_mail = imaplib.IMAP4_SSL(imap_url)
                my_mail.login(self.user, self.password)
                my_mail.select('Inbox')
            
            _, data = my_mail.search(None, search_criteria)
            
            if not data[0]:
                print("No emails found matching the criteria.")
                my_mail.logout()
                return
            
            mail_id_list = data[0].split()  #IDs of all emails that we want to fetch 
            
            msgs = [] # empty list to capture all messages
            #Iterate through messages and extract data into the msgs list
            for num in mail_id_list:
                typ, data = my_mail.fetch(num, '(RFC822)')
                msgs.append(data)
            
            #Print the messages
            for msg in msgs[::-1]:
                for response_part in msg:
                    if type(response_part) is tuple:
                        my_msg=email.message_from_bytes((response_part[1]))
                        print("_________________________________________")
                        print ("subj:", my_msg['subject'])
                        print ("from:", my_msg['from'])
                        print ("body:")
                        for part in my_msg.walk():  
                            if part.get_content_type() == 'text/plain':
                                print (part.get_payload())
            
            print(f"Found {len(mail_id_list)} emails matching criteria")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            try:
                my_mail.logout()
            except:
                pass
        print("Email retrieval completed\n")

    def send_email(self, recipient_email, subject, body, attachments=None):
        print(f"\n=== Sending email to {recipient_email} ===")
        print(f"Subject: {subject}")
        """
        Send an email using Gmail SMTP server
        
        Parameters:
        recipient_email (str): Email address of the recipient
        subject (str): Subject of the email
        body (str): Body content of the email
        attachments (list): Optional list of file paths to attach
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        import os

        # Create the MIME object
        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Add body to email
        msg.attach(MIMEText(body, 'plain'))

        # Add attachments if any
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        attachment = MIMEApplication(f.read(), _subtype=os.path.splitext(file_path)[1][1:])
                        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))
                        msg.attach(attachment)

        try:
            # Create SMTP session
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()  # Enable TLS
            
            # Login using the same credentials from your YAML file
            server.login(self.user, self.password)
            
            # Send email
            server.send_message(msg)
            print("Email sent successfully!")
            
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
        
        finally:
            try:
                server.quit()
            except:
                pass
        print("Email sending process completed\n")

    def create_task_plan(self, task_description):
        """
        Uses Ollama's Granite model to analyze task and create execution plan
        
        Parameters:
        task_description (str): Natural language description of what needs to be done
        """
        print(f"\n=== Creating Task Plan for: {task_description} ===")
        
        # Get current date
        from datetime import datetime
        current_date = datetime.now().strftime("%d-%b-%Y")
        
        # Create system prompt that explains available tools and expected output format
        system_prompt = f"""You are a task planning assistant. When analyzing a task, output only a list of tool calls with their exact parameters, and nothing else. If the task requires multiple steps, include separate calls for each required tool in the order they should be executed.

        List of tools to use:
        - retrieve_emails(sender_email="vaibhav@example.com", start_date="20-Feb-2024", end_date="21-Feb-2024")
        - send_email(recipient_email="someone@example.com", subject="Meeting Notes", body="Hello, attached are the notes.", attachments=["notes.pdf"])
        """
        try:
            # Call Ollama's Granite model
            response = ollama.chat(model='granite3.1-dense:8b', messages=[
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': task_description
                }
            ])
            
            # Print the plan
            print("\nGenerated Task Plan:")
            print(response['message']['content'])
            
            return response['message']['content']
            
        except Exception as e:
            print(f"Error generating task plan: {str(e)}")
            return None

# Example usage:
master = MasterLLM()
master.create_task_plan("Check emails from Vaibhav from yesterday. His email is vaibhav.mehra.in@gmail.com, and then send him a hello message please")