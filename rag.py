# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 00:29:02 2026

@author: TKU
"""

# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
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
# Load Website（6頁）
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
            for i in range(0, len(words), 150):
                chunks.append((tag, " ".join(words[i:i+150])))

        print("✅ RAG ready!")


# =========================
# Routing（避免抓錯頁）
# =========================
def route(q):
    q = q.lower()

    if "name" in q or "who" in q or "誰" in q:
        return ["profile"]

    if "publication" in q or "發表" in q or "paper" in q:
        return ["publication"]

    if "work" in q or "experience" in q or "經歷" in q:
        return ["teaching"]

    if "award" in q or "獎" in q:
        return ["award"]

    if "hobby" in q or "興趣" in q or "愛好" in q:
        return ["hobby"]

    return ["profile", "publication"]


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
# 🔥 清理 context（關鍵）
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
# 🔥 強化 publication 抽取
# =========================
def focus_publication(context, question):
    if "publication" in question.lower() or "發表" in question:
        parts = context.split("20")

        results = []
        for p in parts:
            if len(p.strip()) > 20:
                results.append("20" + p.strip())

        return " ".join(results[:3])

    return context


# =========================
# LLM（ChatGPT風格）
# =========================
def call_llm(context, question):

    prompt = f"""
You are a helpful assistant.

Answer naturally like ChatGPT.

Rules:
- Use 1–2 short sentences
- Focus on key information only
- Do NOT repeat words
- Do NOT include irrelevant details
- If unsure, say "I’m not sure"

Context:
{context}

Question:
{question}

Answer:
"""

    try:
        res = llm(
            prompt,
            max_new_tokens=80,
            do_sample=True,
            temperature=0.7
        )
        return res[0]["generated_text"]
    except:
        return "Error"


# =========================
# API
# =========================
@app.route("/")
def home():
    return "RAG system running"


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        q = data.get("message", "")

        print("Q:", q)

        init_rag()

        docs = retrieve(q)
        context = " ".join(docs)

        # 🔥 關鍵優化
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