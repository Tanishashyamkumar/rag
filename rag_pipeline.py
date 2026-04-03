import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from pypdf import PdfReader
from groq import Groq

# 🔑 API key
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Embedding
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Global DB
db = None

# DB path
DB_PATH = "faiss_index"


# ---------------------------
# 🔹 Load DB
# ---------------------------
def load_db():
    global db
    if os.path.exists(DB_PATH):
        db = FAISS.load_local(
            DB_PATH,
            embedding,
            allow_dangerous_deserialization=True
        )


# ---------------------------
# 🔹 Save DB
# ---------------------------
def save_db():
    if db is not None:
        db.save_local(DB_PATH)


# ---------------------------
# 🔹 Process PDF (WITH PAGE REFERENCES 🔥)
# ---------------------------
def process_pdf(file_path):
    global db

    reader = PdfReader(file_path)

    splitter = CharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    texts = []
    metadatas = []

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()

        if page_text:
            split_chunks = splitter.split_text(page_text)

            for chunk in split_chunks:
                texts.append(chunk)
                metadatas.append({
                    "page": i + 1,
                    "source": file_path
                })

    # Create / update DB
    if db is None:
        db = FAISS.from_texts(texts, embedding, metadatas=metadatas)
    else:
        db.add_texts(texts, metadatas=metadatas)

    save_db()


# ---------------------------
# 🔹 Reset DB
# ---------------------------
def reset_database():
    global db

    if os.path.exists(DB_PATH):
        import shutil
        shutil.rmtree(DB_PATH)

    db = None


# ---------------------------
# 🔹 Get Answer
# ---------------------------
def get_answer(question, model_name, style="paragraph"):
    global db

    if db is None:
        return {
            "answer": "Please upload a document first.",
            "sources": []
        }

    docs = db.similarity_search(question, k=3)

    context = ""
    sources = []

    for doc in docs:
        context += doc.page_content + "\n"

        # 🔥 REAL SOURCE EXTRACTION
        page = doc.metadata.get("page", "unknown")
        source = doc.metadata.get("source", "unknown")

        sources.append(f"{source} - Page {page}")

    # 🔥 remove duplicates
    sources = list(set(sources))

    # 🎯 Style control
    if style == "bullet":
        style_instruction = "Answer in bullet points."
    elif style == "short":
        style_instruction = "Give a very short answer."
    else:
        style_instruction = "Give a clear paragraph answer."

    prompt = f"""
    You are a helpful AI assistant.

    Answer ONLY from the given context.
    If the answer is not in the context, respond politely like:
    "I'm not completely sure based on the provided document."

    {style_instruction}

    Context:
    {context}

    Question:
    {question}
    """

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model_name,
        )

        answer = response.choices[0].message.content.strip()

        return {
            "answer": answer,
            "sources": sources
        }

    except Exception:
        return {
            "answer": "Something went wrong. Please try again.",
            "sources": []
        }