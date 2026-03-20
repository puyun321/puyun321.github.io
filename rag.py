# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 00:29:02 2026

@author: TKU
"""

# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from huggingface_hub import InferenceClient
import os

os.environ.setdefault("HF_TOKEN", "")  # Set HF_TOKEN in your environment before running

# =========================
# Flask
# =========================
app = Flask(__name__)
CORS(app)

# =========================
# 🔑 Hugging Face（用環境變數）
# =========================
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    token=os.getenv("HF_TOKEN")
)

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
# 🧠 輕量 RAG（關鍵字檢索）
# =========================
def retrieve(query, chunks, top_k=3):
    query_words = query.lower().split()
    scored = []

    for c in chunks:
        score = sum(word in c.lower() for word in query_words)
        if score > 0:
            scored.append((score, c))

    scored.sort(reverse=True)

    # fallback（避免抓不到）
    if not scored:
        return chunks[:top_k]

    return [c for _, c in scored[:top_k]]

# =========================
# 🤖 LLM
# =========================
def call_llm(prompt):
    try:
        response = client.chat_completion(
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )

        return response.choices[0].message["content"]

    except Exception as e:
        print("HF ERROR:", repr(e))
        return f"❌ HF錯誤: {repr(e)}"

# =========================
# 🚀 Lazy loading（避免啟動爆記憶體）
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
    init_rag()  # ⭐ 延遲初始化

    data = request.get_json()
    user_msg = data.get("message", "")

    print("收到問題：", user_msg)

    docs = retrieve(user_msg, chunks)
    context = "\n".join(docs)

    prompt = f"""
你是邱普運教授的AI助理，請根據資料回答問題。

規則：
- 用自然中文回答
- 不要重複句子
- 不要輸出提示詞
- 若資料不足請說不知道

資料：
{context}

問題：
{user_msg}

回答：
"""

    answer = call_llm(prompt)

    return jsonify({"reply": answer})

# =========================
# Render 啟動（保險）
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)