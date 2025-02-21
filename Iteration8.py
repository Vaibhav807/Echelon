import ollama
import imaplib
import email
import yaml  
import ast

with open("details.yml") as f:
    content = f.read()
    
# from credentials.yml import user name and password
my_credentials = yaml.load(content, Loader=yaml.FullLoader)

#Load the user name and passwd from yaml file
user, password = my_credentials["user"], my_credentials["password"]

def retrieve_emails(sender_email, start_date, end_date):
    print("\n" + "="*50)
    print(f"📧 RETRIEVING EMAILS")
    print(f"From: {sender_email}")
    print(f"Date Range: {start_date} to {end_date}")
    print("="*50 + "\n")

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
            print("\n❌ No emails found matching the criteria.")
            my_mail.logout()
            return
            
        mail_id_list = data[0].split()  #IDs of all emails that we want to fetch 
        print(f"\n📬 Found {len(mail_id_list)} emails matching your criteria.\n")
        
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
                    print("="*40)
                    print(f"📌 Subject: {my_msg['subject']}")
                    print(f"👤 From: {my_msg['from']}")
                    print(f"📝 Body:")
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
    print("\n" + "="*50)
    print("📤 SENDING EMAIL")
    print(f"To: {recipient_email}")
    print(f"Subject: {subject}")
    if attachments:
        print(f"Attachments: {len(attachments)} file(s)")
    print("="*50 + "\n")

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
        print("\n✅ Email sent successfully!")
        
    except Exception as e:
        print(f"\n❌ Failed to send email: {str(e)}")
        
    finally:
        try:
            server.quit()
        except:
            pass

def summarize_content(content):
    """
    Uses Ollama's Granite model to create a summary of the given content
    
    Parameters:
    content (str): The text content to summarize
    Returns:
    str: The generated summary
    """
    print("\n" + "="*50)
    print("📝 GENERATING SUMMARY")
    print("="*50 + "\n")

    try:
        # Create system prompt for summarization
        system_prompt = """You are a summarization assistant. Please provide a concise summary of the given content. 
        Focus on key points and main ideas. Keep the summary clear and informative."""

        # Call Ollama's Granite model
        response = ollama.chat(model='granite3.1-dense:8b', messages=[
            {
                'role': 'system',
                'content': system_prompt
            },
            {
                'role': 'user',
                'content': f"Please summarize this content:\n\n{content}"
            }
        ])
        
        summary = response['message']['content']
        
        print("\n✅ Summary generated successfully!")
        print("\nSummary:")
        print("-"*30)
        print(summary)
        print("-"*30)
        
        return summary
        
    except Exception as e:
        print(f"\n❌ Error generating summary: {str(e)}")
        return None

def create_task_plan(task_description):
    """
    Uses Ollama's Granite model to analyze task and create execution plan
    
    Parameters:
    task_description (str): Natural language description of what needs to be done
    Returns:
    str: The generated plan that will be executed
    """
    from datetime import datetime
    current_date = datetime.now().strftime("%d-%b-%Y")
    
    print(f"\n=== Creating Task Plan for: {task_description} ===")
    
    # Create system prompt that explains available tools and expected output format
    system_prompt = f"""You are a task planning assistant. When analyzing a task, output only a list of tool calls with their exact parameters, and nothing else. Do not add any numbering or prefixes.

    Current date is: {current_date}

    List of tools to use:
    - retrieve_emails(sender_email="someone@example.com", start_date="DD-MMM-YYYY", end_date="DD-MMM-YYYY")
    - send_email(recipient_email="someone@example.com", subject="...", body="...", attachments=[...])
    - summarize_content(content="...") 
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
        
        plan = response['message']['content']
        
        # Print the plan
        print("\nGenerated Task Plan:")
        print(plan)
        
        return plan
        
    except Exception as e:
        print(f"Error generating task plan: {str(e)}")
        return None

def execute_task_plan(plan):
    """
    Executes a task plan generated by create_task_plan
    
    Parameters:
    plan (str): The plan containing function calls to execute
    """
    if not plan:
        print("No plan to execute")
        return
        
    print("\nExecuting Task Plan:")
    for line in plan.strip().split('\n'):
        if line.strip():  # Skip empty lines
            try:
                # Execute the function call
                print(f"Executing: {line}")
                eval(line)
            except Exception as e:
                print(f"Error executing {line}: {str(e)}")

def create_priority_list(unorganized_input):
    """
    Uses Ollama's Granite model to analyze unorganized information and create 
    a sequential task list in order of recommended completion.
    """
    import ast

    print("\n" + "="*50)
    print("🔄 ORGANIZING TASKS")
    print("="*50 + "\n")

    system_prompt = """You are a task organization assistant. Given unorganized information, create a sequential list 
    of clear, actionable tasks in the order they should be completed. Consider:
    
    1. Dependencies between tasks
    2. Urgency and deadlines
    3. Logical workflow order
    4. Resource availability
    
    Format your response as a valid Python list of dictionaries. Each dictionary should have these exact keys:
    {
        'task': 'The clear action to take',
        'order': 1,  # Sequential number
        'reason': 'Why this task should be done at this point',
        'dependencies': 'What needs to be completed first (or empty string if none)',
        'estimated_time': 'How long it should take'
    }
    
    Important: Use only straight quotes (') and ensure the response is valid Python syntax.
    """

    try:
        response = ollama.chat(model='granite3.1-dense:8b', messages=[
            {
                'role': 'system',
                'content': system_prompt
            },
            {
                'role': 'user',
                'content': f"Please organize this information into sequential tasks:\n\n{unorganized_input}"
            }
        ])

        # Clean and validate the model response
        response_text = response['message']['content']
        response_text = response_text.replace('```python', '').replace('```', '').strip()

        try:
            # Try to parse the response as a Python literal
            task_list = ast.literal_eval(response_text)

            # Validate its structure
            if not isinstance(task_list, list):
                raise ValueError("Response is not a list")

            for task in task_list:
                if not all(key in task for key in ['task', 'order', 'reason', 'dependencies', 'estimated_time']):
                    raise ValueError("Task missing required fields")

        except (SyntaxError, ValueError) as e:
            print(f"\n⚠️ Could not parse model response. Using simplified format.")
            # Fallback: split the response into lines and make a task from each nonempty line.
            lines = response_text.split('\n')
            task_list = []
            for line in lines:
                line = line.strip()
                if line:
                    # If a dash exists, use the text after the dash as the task description
                    if '-' in line:
                        task_desc = line.split('-', 1)[-1].strip()
                    else:
                        task_desc = line
                    if task_desc:
                        task_list.append({
                            'task': task_desc,
                            'order': len(task_list) + 1,
                            'reason': 'Fallback parsed task',
                            'dependencies': '',
                            'estimated_time': 'Not specified'
                        })
            # If no tasks were found, use the entire response as one task.
            if not task_list and response_text:
                task_list = [{
                    'task': response_text,
                    'order': 1,
                    'reason': 'Fallback, raw response',
                    'dependencies': '',
                    'estimated_time': 'Not specified'
                }]

        # Print the organized task list
        print("\n📋 Sequential Task List:")
        print("="*50)
        for task in task_list:
            print(f"\n#{task['order']} - {task['task']}")
            print(f"⏱️  Estimated time: {task['estimated_time']}")
            print(f"🔄 Dependencies: {task['dependencies'] if task['dependencies'] else 'None'}")
            print(f"📝 Reason: {task['reason']}")
            print("-"*30)

        return task_list

    except Exception as e:
        print(f"\n❌ Error organizing tasks: {str(e)}")
        return None

# Test example
test_input = """
Need to launch new product page on website. Marketing team sent over new product photos 
yesterday but they need editing. Content team is still working on product descriptions.
Have to coordinate with the dev team for implementation. Also need to set up analytics 
tracking. Legal team needs to review before we go live. Social media announcements 
should go out after launch. CEO wants a report on the launch metrics next week.

Also remember to schedule team meeting to discuss Q4 planning, but that can wait until 
after the launch. Oh, and the old product pages need to be archived.
"""

organized_tasks = create_priority_list(test_input)


