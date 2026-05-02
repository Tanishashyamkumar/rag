import os
import re
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from pypdf import PdfReader
from groq import Groq

from nltk.tokenize import sent_tokenize
import nltk
nltk.download('punkt')

# 🔥 NLP
import spacy
from transformers import pipeline

nlp = spacy.load("en_core_web_sm")

# 🔥 Small fast model
nli = pipeline("text-classification", model="valhalla/distilbart-mnli-12-3")

# 🔑 API key
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")

db = None
DB_PATH = "faiss_index"


# ---------------------------
# 🔹 Text Cleaning
# ---------------------------
def clean_text(text):
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text


# ---------------------------
# 🔹 Intent Classification
# ---------------------------
def classify_intent(question):
    q = question.lower()

    if "compare" in q:
        return "comparison"
    elif "summarize" in q:
        return "summary"
    elif "how" in q:
        return "procedural"
    else:
        return "factual"


# ---------------------------
# 🔹 Coreference
# ---------------------------
def resolve_coref(question):
    return question.replace(" it ", " the topic ").replace(" he ", " the person ")


# ---------------------------
# 🔹 Load DB
# ---------------------------
def load_db():
    global db
    if os.path.exists(DB_PATH):
        db = FAISS.load_local(DB_PATH, embedding, allow_dangerous_deserialization=True)


# ---------------------------
# 🔹 Save DB
# ---------------------------
def save_db():
    if db is not None:
        db.save_local(DB_PATH)


# ---------------------------
# 🔹 Process PDF
# ---------------------------
def process_pdf(file_path):
    global db

    reader = PdfReader(file_path)
    texts, metadatas = [], []

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()

        if page_text:
            cleaned = clean_text(page_text)
            sentences = sent_tokenize(cleaned)

            temp, grouped = "", []

            for sent in sentences:
                temp += sent + " "
                if len(temp) > 200:
                    grouped.append(temp.strip())
                    temp = ""

            if temp:
                grouped.append(temp.strip())

            for chunk in grouped:
                texts.append(chunk)
                metadatas.append({"page": i + 1, "source": file_path})

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
# 🔹 Get Answer (FINAL 🔥)
# ---------------------------
def get_answer(question, model_name, style="paragraph"):
    global db

    if db is None:
        return {"answer": "Please upload a document first.", "sources": [], "mindmap": ""}

    # 🔥 Coref + Intent
    question = resolve_coref(question)
    intent = classify_intent(question)

    # 🔥 Intent instruction
    if intent == "comparison":
        intent_instruction = "Compare clearly using bullet points with differences."
    elif intent == "summary":
        intent_instruction = "Give a structured summary."
    elif intent == "procedural":
        intent_instruction = "Explain step-by-step."
    else:
        intent_instruction = "Give a clear explanation."

    # 🔥 NER
    doc_nlp = nlp(question)
    entities = [ent.text for ent in doc_nlp.ents]

    # 🔥 Retrieval
    k = 3
    if intent == "summary":
        k = 6
    elif intent == "comparison":
        k = 5
    elif intent == "procedural":
        k = 4

    docs = db.similarity_search(question, k=k)

    for ent in entities:
        docs.extend(db.similarity_search(ent, k=1))

    unique_docs, seen = [], set()

    for doc in docs:
        if doc.page_content not in seen:
            unique_docs.append(doc)
            seen.add(doc.page_content)

    docs = unique_docs[:5]

    context, sources = "", []

    for doc in docs:
        context += doc.page_content + "\n"
        page = doc.metadata.get("page", "unknown")
        source = doc.metadata.get("source", "unknown")
        sources.append(f"{source} - Page {page}")

    sources = list(set(sources))

    # 🔥 Prompt (FIXED)
    prompt = f"""
You are a strict AI assistant.

You MUST follow the output format EXACTLY.
DO NOT explain.
DO NOT write paragraphs.
ONLY generate structured output.

========================

Answer:
- Give concise bullet points

Mindmap:
Artificial Intelligence
- Definition
  - What AI is
- Types
  - Narrow AI
  - General AI
- Applications
  - Healthcare
  - Robotics

========================

Rules:
- ALWAYS include "Mindmap:"
- ALWAYS use "-" for structure
- DO NOT skip sections
- DO NOT explain anything outside format

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

        output = response.choices[0].message.content.strip()

        final_answer, mindmap = output, ""

        # 🔥 Robust extraction
        if "Mindmap:" in output:
            parts = output.split("Mindmap:")
            final_answer = parts[0].replace("Answer:", "").strip()
            mindmap = parts[1].strip()

        elif "Mind Map:" in output:
            parts = output.split("Mind Map:")
            final_answer = parts[0].strip()
            mindmap = parts[1].strip()

        else:
            lines = output.split("\n")
            mindmap_lines = [l for l in lines if l.strip().startswith("-")]

            if mindmap_lines:
                mindmap = "\n".join(mindmap_lines)
                final_answer = "\n".join([l for l in lines if not l.strip().startswith("-")]).strip()

        # 🔥 Faithfulness (only contradiction)
        try:
            result = nli(f"{context} </s> {final_answer}")
            if result[0]['label'] == "CONTRADICTION":
                final_answer = "⚠️ This answer may not be fully supported.\n\n" + final_answer
        except:
            pass

        return {
            "answer": final_answer,
            "sources": sources,
            "mindmap": mindmap
        }

    except Exception as e:
        print("🔥 ERROR:", e)
        return {"answer": str(e), "sources": [], "mindmap": ""}