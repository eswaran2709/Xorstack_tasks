import os
from flask import Flask, request, jsonify, render_template
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from transformers import pipeline
import chromadb

app = Flask(__name__)

# --- CONFIGURATION ---
CHROMA_API_KEY = 'ck-8e8GrqDmTRudLTpZoLkpwarzTeZCDQR1ESEPfnB6gNsK'
TENANT_ID = '5e3fc84d-0f55-4a18-b1ae-6df72821f777'
DATABASE_NAME = 'xorstack'
COLLECTION_NAME = "RAG_Bot"
DATA_DIR = "./data"

os.makedirs(DATA_DIR, exist_ok=True)

# --- 1. INITIALIZE MODELS ---
print("Loading Embedding Model (MiniLM)...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

print("Loading LLM (Flan-T5)...")
llm = pipeline("text2text-generation", model="google/flan-t5-base", max_new_tokens=256)

# --- 2. VECTOR DATABASE SETUP ---
client = chromadb.CloudClient(
    api_key=CHROMA_API_KEY,
    tenant=TENANT_ID,
    database=DATABASE_NAME
)

# Ensure collection exists
client.get_or_create_collection(name=COLLECTION_NAME)

vector_db = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    client=client
)

# --- 3. DOCUMENT PROCESSING ---
def ingest_docs():
    docs = []
    files = os.listdir(DATA_DIR)
    if not files:
        return 0
        
    for file in files:
        path = os.path.join(DATA_DIR, file)
        if file.endswith(".pdf"):
            loader = PyPDFLoader(path)
            docs.extend(loader.load())
        elif file.endswith(".txt"):
            loader = TextLoader(path)
            docs.extend(loader.load())
    
    if docs:
        # CHUNKING STRATEGY: 700 chars with 100 overlap for context retention
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
        chunks = text_splitter.split_documents(docs)
        vector_db.add_documents(chunks)
        return len(chunks)
    return 0

# --- 4. ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ingest', methods=['POST'])
def handle_ingest():
    num_chunks = ingest_docs()
    return jsonify({"message": f"Successfully processed {num_chunks} chunks."})

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_query = data.get("query")
    
    # RETRIEVAL QUALITY: Use MMR to find relevant but diverse chunks
    retrieved_docs = vector_db.max_marginal_relevance_search(user_query, k=3)
    
    # Debug print to terminal
    print(f"\nUser Query: {user_query}")
    print(f"Retrieved {len(retrieved_docs)} chunks.")

    if not retrieved_docs:
        return jsonify({"answer": "Not available (No context found).", "sources": []})

    context = "\n\n".join([d.page_content for d in retrieved_docs])
    
    # ANSWER RELIABILITY: Explicit instruction to avoid hallucinations
    prompt = f"""Answer the question based ONLY on the context. If you don't know, say 'Not available'.
    Context: {context}
    Question: {user_query}
    Answer:"""
    
    result = llm(prompt)
    answer = result[0]["generated_text"]
    
    # Extract source filenames for the dashboard
    sources = list(set(os.path.basename(d.metadata.get("source", "Unknown")) for d in retrieved_docs))
    
    return jsonify({"answer": answer, "sources": sources})

if __name__ == "__main__":
    app.run(debug=True, port=5000)