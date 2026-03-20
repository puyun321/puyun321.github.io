# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 00:29:02 2026

@author: TKU
"""

# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = ""

app = Flask(__name__)
CORS(app)

# =========================
# Embedding
# =========================
embed_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2",
    device="cpu"
)

# =========================
# LLM
# =========================
llm = pipeline(
    "text2text-generation",
    model="google/flan-t5-base",
    device=-1
)

chunks = []

# =========================
# Semantic routing
# =========================
page_descriptions = {
    "profile": "personal information name biography background",
    "publication": "research papers journal publications conference articles",
    "work": "projects AI applications systems development personal work",
    "award": "awards honors achievements competition prizes",
    "teaching": "working experience career job position professor researcher",
    "hobby": "hobbies interests travel leisure activities"
}

page_keys = list(page_descriptions.keys())
page_embs = embed_model.encode(list(page_descriptions.values()))

# =========================
# Load website
# =========================
def load_website():
    urls = [
        ("profile", "https://puyun321.github.io/"),
        ("publication", "https://puyun321.github.io/Publication"),
        ("work", "https://puyun321.github.io/Personal_work"),
        ("award", "https://puyun321.github.io/Academic_Award"),
        ("teaching", "https://puyun321.github.io/Teaching_Experience"),
        ("hobby", "https://puyun321.github.io/My_Hobbies")
    ]

    data = {}

    for tag, url in urls:
        try:
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")

            for t in soup(["script", "style"]):
                t.extract()

            text = soup.get_text(separator=" ")
            data[tag] = text

        except:
            data[tag] = ""

    return data

# =========================
# Init RAG
# =========================
def init_rag():
    global chunks

    if not chunks:
        print("🔄 Loading RAG...")

        data = load_website()

        chunks = []
        for tag, text in data.items():
            words = text.split()

            # 🔥 smaller chunks（更準）
            for i in range(0, len(words), 80):
                chunks.append((tag, " ".join(words[i:i+80])))

        print("✅ RAG ready!")

# =========================
# Semantic routing
# =========================
def route(query):
    q_emb = embed_model.encode([query])[0]
    scores = np.dot(page_embs, q_emb)

    top_idx = np.argsort(scores)[-2:]
    return [page_keys[i] for i in top_idx]

# =========================
# Retrieve
# =========================
def retrieve(query, top_k=3):
    allowed = route(query)

    filtered = [c for c in chunks if c[0] in allowed]
    if not filtered:
        filtered = chunks

    texts = [c[1] for c in filtered]

    emb = embed_model.encode(texts)
    q_emb = embed_model.encode([query])[0]

    scores = np.dot(emb, q_emb)
    top_idx = np.argsort(scores)[-top_k:][::-1]

    return [texts[i] for i in top_idx]

# =========================
# Clean context
# =========================
def clean_context(text):
    words = text.split()

    blacklist = [
        "Home", "Profile", "Contact", "Email",
        "Back", "More", "Details", "Support",
        "ResearchGate", "Other", "Personal"
    ]

    cleaned = [w for w in words if w not in blacklist]

    return " ".join(cleaned[:300])

# =========================
# 🔥 Publication extraction
# =========================
def focus_publication(context, question):
    q = question.lower()

    if "publication" in q or "發表" in q:

        matches = re.findall(r"(20\d{2}[^.]+)", context)

        # recent → 只抓 2024/2025
        if "recent" in q:
            matches = [m for m in matches if m.startswith("2024") or m.startswith("2025")]

        unique = []
        for m in matches:
            if m not in unique:
                unique.append(m)

        return " ".join(unique[:3])

    return context

# =========================
# LLM
# =========================
def call_llm(context, question):

    q = question.lower()

    if "name" in q or "名字" in q:
        task = "Give ONLY the person's name."
    elif "who" in q or "是誰" in q:
        task = "Describe who the person is in ONE short sentence."
    elif "publication" in q or "發表" in q:
        task = "List 2-3 key publications briefly."
    elif "hobby" in q or "興趣" in q:
        task = "Describe hobbies briefly."
    elif "work" in q or "experience" in q or "經歷" in q:
        task = "Summarize work experience in one sentence."
    else:
        task = "Answer briefly."

    prompt = f"""
You are a precise assistant.

Task:
{task}

Rules:
- VERY SHORT answer
- No explanation
- No repetition
- No irrelevant text
- If not found, say "Not sure"

Context:
{context}

Question:
{question}

Answer:
"""

    try:
        res = llm(
            prompt,
            max_new_tokens=50,
            do_sample=False
        )

        ans = res[0]["generated_text"].strip()

        # 🔥 remove repetition
        ans = re.sub(r"\b(\w+)( \1\b)+", r"\1", ans)

        if len(ans) > 120:
            ans = ans[:120]

        if ans.count("PU YUN") > 3:
            return "Not sure"

        return ans

    except:
        return "Error"

# =========================
# API
# =========================
@app.route("/")
def home():
    return "RAG running"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        q = data.get("message", "")

        print("Q:", q)

        init_rag()

        docs = retrieve(q)
        context = " ".join(docs)

        context = clean_context(context)
        context = focus_publication(context, q)

        answer = call_llm(context, q)

        return jsonify({"reply": answer})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"reply": "error"})

# =========================
# Run
# =========================
if __name__ == "__main__":
    init_rag()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)