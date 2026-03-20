# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 00:29:02 2026

@author: TKU
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
import os

os.environ.setdefault("HF_TOKEN", "")  # Set HF_TOKEN in your environment before running
# os.environ.setdefault("HF_TOKEN", "")  # Set HF_TOKEN in your environment before running
app = Flask(__name__)
CORS(app)

# =========================
# 🔑 Hugging Face（官方SDK）
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
# 🧠 真 embedding（升級重點）
# =========================
embed_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

def build_index(chunks):
    embeddings = embed_model.encode(chunks)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype("float32"))
    return index, embeddings

# =========================
# 🔍 檢索
# =========================
def retrieve(query, chunks, index):
    q_emb = embed_model.encode([query])
    D, I = index.search(np.array(q_emb).astype("float32"), k=3)
    return [chunks[i] for i in I[0]]

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
        print("HF ERROR:", repr(e))   # ⭐ 用 repr 才看得到
        return f"❌ HF錯誤: {repr(e)}"

# =========================
# 🚀 初始化（只跑一次）
# =========================
print("🔄 Loading RAG...")
texts = load_website()
chunks = split_text(texts)
index, embeddings = build_index(chunks)
print("✅ RAG ready!")

# =========================
# 💬 API
# =========================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "RAG server running"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "")

    print("收到問題：", user_msg)

    docs = retrieve(user_msg, chunks, index)
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
# 🔥 Render 啟動
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)