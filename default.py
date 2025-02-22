import requests
from bs4 import BeautifulSoup
import numpy as np

# pip install ollama
import ollama

import chromadb
from chromadb.utils import embedding_functions

################################################################################
# 1. Download some web pages and chunk them
################################################################################

URLS = [
    "https://www.ibm.com/case-studies/us-open",
    "https://www.ibm.com/sports/usopen",
    "https://newsroom.ibm.com/US-Open-AI-Tennis-Fan-Engagement",
    "https://newsroom.ibm.com/2024-08-15-ibm-and-the-usta-serve-up-new-and-enhanced-generative-ai-features-for-2024-us-open-digital-platforms",
]

def fetch_text_from_url(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("p")
    text = "\n".join(p.get_text() for p in paragraphs)
    return text

# Combine texts from all pages
all_texts = []
for url in URLS:
    all_texts.append(fetch_text_from_url(url))
combined_text = "\n".join(all_texts)

def chunk_text(text, chunk_size=300, overlap=50):
    """Simple word-based chunking with overlap."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = words[start:end]
        chunks.append(" ".join(chunk))
        start += (chunk_size - overlap)
    return chunks

doc_chunks = chunk_text(combined_text, chunk_size=300, overlap=50)

################################################################################
# 2. Use Ollama's Python client to embed each chunk
################################################################################

class CustomOllamaEmbedding:
    def __init__(self, model_name="granite-embedding:30m"):
        self.client = ollama.Client()
        self.model_name = model_name
    
    def __call__(self, input):
        if isinstance(input, str):
            input = [input]
        
        embeddings = []
        for text in input:
            response = self.client.embeddings(model=self.model_name, prompt=text)
            embeddings.append(response['embedding'])
        return embeddings

# Initialize ChromaDB with persistence
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.create_collection(
    name="us_open_docs",
    embedding_function=CustomOllamaEmbedding()
)

# Add documents to the vector database
collection.add(
    documents=doc_chunks,
    ids=[f"chunk_{i}" for i in range(len(doc_chunks))]
)

################################################################################
# 3. Simple retrieval by cosine similarity
################################################################################

def retrieve(query, top_k=3):
    """Given a query, find top_k chunk(s) using ChromaDB."""
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    return results['documents'][0]  # First element because query_texts was a single query

################################################################################
# 4. Final answer generation with "granite3.1-dense:8b"
################################################################################

# Create a separate client for generation
gen_client = ollama.Client()

def generate_answer(context, question):
    """
    Pass context + question to the LLM to produce a final answer.
    The context is a set of retrieved chunks.
    """
    prompt = f"""
Use the context below to answer the question accurately. 
If you don't have enough info, say so.

Context:
\"\"\"
{context}
\"\"\"

Question: {question}
Answer:
""".strip()

    # Generate with model specified in the call
    response = gen_client.generate(model="granite3.1-dense:8b", prompt=prompt)
    # Extract just the response text
    return response.get('response', 'No response generated')

################################################################################
# 5. Putting it all together
################################################################################

def ask(question):
    # 1) retrieve relevant chunks
    top_chunks = retrieve(question, top_k=2)
    context = "\n---\n".join(top_chunks)
    # 2) generate
    answer = generate_answer(context, question)
    return answer

################################################################################
# 6. Example Usage
################################################################################

if __name__ == "__main__":
    q1 = "What sport is played at the US Open?"
    print("Q:", q1)
    print("A:", ask(q1), "\n")

    q2 = "How did IBM use watsonx at the 2024 US Open?"
    print("Q:", q2)
    print("A:", ask(q2), "\n")

    q3 = "What is the capital of France?"
    print("Q:", q3)
    print("A:", ask(q3), "\n")
