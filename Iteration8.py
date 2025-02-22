import sys
import PyPDF2
import numpy as np

# pip install ollama
import ollama

import chromadb
from chromadb.utils import embedding_functions

################################################################################
# 1. Extract text from the PDF file and chunk it
################################################################################

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

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

################################################################################
# 3. Final answer generation with "granite3.1-dense:8b"
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
You must follow the exact format requirements in the question (like number of sentences).
If you don't have enough info, say so.

Context:
\"\"\"
{context}
\"\"\"

Question: {question}
Answer (follow format requirements strictly):
""".strip()

    response = gen_client.generate(model="granite3.1-dense:8b", prompt=prompt)
    return response.get('response', 'No response generated')

################################################################################
# 4. Retrieval function
################################################################################

# Note: The 'collection' variable will be initialized in the __main__ block.
def retrieve(query, top_k=3):
    """Given a query, find top_k chunk(s) using ChromaDB."""
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    return results['documents'][0]  # Use the returned chunk list for the single query

def ask(question):
    """
    Retrieve relevant chunks and generate an answer.
    Relies on the global 'collection' variable.
    """
    top_chunks = retrieve(question, top_k=2)
    context = "\n---\n".join(top_chunks)
    answer = generate_answer(context, question)
    return answer

################################################################################
# 5. Main execution: process the specific PDF file
################################################################################

if __name__ == "__main__":
    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    try:
        # Try to get existing collection
        collection = chroma_client.get_collection(
            name="document_chunks",
            embedding_function=CustomOllamaEmbedding()
        )
        print("Using existing vector database...")
    
    except ValueError: # Collection doesn't exist
        print("Creating new vector database...")
        # Use the specific PDF file
        pdf_path = "Generative_AI_Hackathon_IBM_Granite_Final.pdf"
        
        # Extract text from the provided PDF file
        combined_text = extract_text_from_pdf(pdf_path)
        doc_chunks = chunk_text(combined_text, chunk_size=300, overlap=50)

        # Create a new collection
        collection = chroma_client.create_collection(
            name="document_chunks",
            embedding_function=CustomOllamaEmbedding()
        )

        # Add document chunks to the vector database
        collection.add(
            documents=doc_chunks,
            ids=[f"chunk_{i}" for i in range(len(doc_chunks))]
        )
        print("Vector database created successfully!")

    ############################################################################
    # 6. Example Usage
    ############################################################################

    # q1 = "WWhat exactly do you have to do in this hackathon?"
    # print("Q:", q1)
    # print("A:", ask(q1), "\n")

    q2 = "What do the winner of the hackathon get?"
    print("Q:", q2)
    print("A:", ask(q2), "\n")
