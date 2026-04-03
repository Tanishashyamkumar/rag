from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel
import os

from rag_pipeline import process_pdf, get_answer, load_db, reset_database

app = FastAPI()

# 🔥 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Request model
class Query(BaseModel):
    question: str
    model: str = "llama-3.3-70b-versatile"
    style: str = "paragraph"   # 🔥 new


# ---------------------------
# 🔹 Load DB on startup
# ---------------------------
@app.on_event("startup")
def startup():
    load_db()


# ---------------------------
# 🔹 Upload Multiple PDFs (FIXED 🔥)
# ---------------------------
# @app.post("/upload")
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "Only PDF files are allowed"}

        os.makedirs("uploads", exist_ok=True)
        file_path = os.path.join("uploads", file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        process_pdf(file_path)

        return {"message": "File uploaded successfully"}

    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# 🔹 Ask Question
# ---------------------------
@app.post("/ask")
def ask_question(query: Query):
    try:
        answer = get_answer(query.question)
        return {"answer": answer}
    except Exception as e:
        return {"answer": str(e)}


# ---------------------------
# 🔹 Reset Database
# ---------------------------
@app.post("/reset")
def reset():
    try:
        reset_database()
        return {"message": "Database reset successful"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# 🔹 Health Check
# ---------------------------
@app.get("/")
def home():
    return {"message": "RAG Backend Running 🚀"}