from flask import Flask, render_template, request, Response
import ollama

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')
    else:
        user_input = request.form['user_input']
        def generate():
            try:
                response_text = "granite3.1-dense:8b"
                for chunk in ollama.chat(
                    model='granite3.1-dense:8b',
                    messages=[{'role': 'user', 'content': user_input}],
                    stream=True
                ):
                    if chunk.get('message', {}).get('content'):
                        content = chunk['message']['content']
                        response_text += content
                        yield content
            except Exception as e:
                yield f"Error: {str(e)}"

        return Response(generate(), content_type='text/plain')

def generate_response(prompt: str) -> str:
    """
    Generate a response using Ollama with the granite model.
    
    Args:
        prompt (str): The input prompt/question
    
    Returns:
        str: The generated response
    """
    try:
        response_text = ""
        for chunk in ollama.chat(
            model='granite3.1-dense:8b',
            messages=[{'role': 'user', 'content': prompt}],
            stream=True
        ):
            if chunk.get('message', {}).get('content'):
                content = chunk['message']['content']
                response_text += content
        
        return response_text
    
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
