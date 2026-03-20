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
from bs4 import BeautifulSoup
# from huggingface_hub import InferenceClient
import os

os.environ.setdefault("HF_TOKEN", "")  # Set HF_TOKEN in your environment before running


# =========================
# Flask
# =========================
app = Flask(__name__)
CORS(app)

# =========================
# 🌐 抓網站內容
# =========================
def load_website():
    urls = [
        "https://puyun321.github.io/",
        "https://puyun321.github.io/Publication",
        "https://puyun321.github.io/Personal_work",
        "https://puyun321.github.io/Academic_Award",
        "https://puyun321.github.io/Teaching_Experience",
        "https://puyun321.github.io/My_Hobbies"
    ]

    texts = []

    for url in urls:
        try:
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")
            text = soup.get_text(separator=" ")
            texts.append(text)
        except:
            continue

    return texts

# =========================
# ✂️ chunk
# =========================
def split_text(texts, chunk_size=200):
    chunks = []
    for text in texts:
        words = text.split()
        for i in range(0, len(words), chunk_size):
            chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks

# =========================
# 🧠 簡單檢索
# =========================
def retrieve(query, chunks, top_k=3):
    query_words = query.lower().split()
    scored = []

    for c in chunks:
        score = sum(word in c.lower() for word in query_words)
        if score > 0:
            scored.append((score, c))

    scored.sort(reverse=True)

    if not scored:
        return chunks[:top_k]

    return [c for _, c in scored[:top_k]]

# =========================
# 🤖 LLM（最穩版本）
# =========================
def call_llm(prompt):
    hf_token = os.getenv("HF_TOKEN")

    if not hf_token:
        return fallback(prompt)

    try:
        headers = {
            "Authorization": f"Bearer {hf_token}"
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 120,
                "temperature": 0.7,
                "return_full_text": False
            }
        }

        response = requests.post(
            "https://router.huggingface.co/hf-inference/models/microsoft/Phi-3-mini-4k-instruct",
            headers=headers,
            json=payload,
            timeout=20
        )

        print("HF status:", response.status_code)
        print("HF raw:", response.text[:200])

        data = response.json()

        # 正常回傳
        if isinstance(data, list):
            return data[0]["generated_text"]

        # HF error
        if "error" in data:
            return fallback(prompt)

        return str(data)

    except Exception as e:
        print("HF ERROR:", repr(e))
        return fallback(prompt)

# =========================
# 🛟 fallback（保證有回答）
# =========================
def fallback(prompt):
    # 抓資料部分
    if "【資料】" in prompt:
        context = prompt.split("【資料】")[1].split("【問題】")[0]
        summary = " ".join(context.split()[:80])
        return f"根據資料，{summary}..."

    return "目前無法取得模型回應"

# =========================
# 🚀 Lazy Loading
# =========================
chunks = None

def init_rag():
    global chunks
    if chunks is None:
        print("🔄 Loading RAG...")
        texts = load_website()
        chunks = split_text(texts)
        print("✅ RAG ready!")

# =========================
# API
# =========================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "RAG server running"})

@app.route("/chat", methods=["POST"])
def chat():
    init_rag()

    data = request.get_json()
    user_msg = data.get("message", "")

    print("收到問題：", user_msg)

    docs = retrieve(user_msg, chunks)
    context = "\n".join(docs)

    prompt = f"""
你是一個專業AI助理，請自然回答。

【資料】
{context}

【問題】
{user_msg}

【回答】
"""

    answer = call_llm(prompt)

    return jsonify({"reply": answer})

# =========================
# Render / local
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)