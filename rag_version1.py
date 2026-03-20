# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
# -*- coding: utf-8 -*-
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
torch.cuda.is_available = lambda: False

from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM
import faiss
import numpy as np
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# =========================
# 🔥 1️⃣ 抓網站資料（真正RAG）
# =========================
def fetch_page(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")

        # 移除垃圾
        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text(separator="\n")
        return text
    except:
        return ""

urls = [
    "https://puyun321.github.io/",
    "https://puyun321.github.io/Publication",
    "https://puyun321.github.io/Personal_work",
    "https://puyun321.github.io/Academic_Award",
    "https://puyun321.github.io/Teaching_Experience",
    "https://puyun321.github.io/My_Hobbies"
]

raw_docs = [fetch_page(u) for u in urls]

# =========================
# 🔥 2️⃣ 切 chunk（超重要）
# =========================
def split_text(text, chunk_size=300):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
    return chunks

documents = []
for doc in raw_docs:
    documents.extend(split_text(doc))

print(f"✅ 載入文件數量: {len(documents)}")

# =========================
# 3️⃣ Embedding
# =========================
embed_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
doc_embeddings = embed_model.encode(documents)

# =========================
# 4️⃣ FAISS
# =========================
dimension = doc_embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(doc_embeddings))

# =========================
# 🔥 5️⃣ LLM（Qwen）
# =========================
model_name = "Qwen/Qwen2.5-0.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float32
)

def generate_answer(prompt):
    messages = [
        {"role": "system", "content": "你是專業且簡潔的AI助理"},
        {"role": "user", "content": prompt}
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(text, return_tensors="pt")

    outputs = model.generate(
        **inputs,
        max_new_tokens=120,
        do_sample=True,
        temperature=0.7,
        top_p=0.9
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # 🔥 清掉 prompt 污染
    if "assistant" in response:
        response = response.split("assistant")[-1]

    return response.strip()

# =========================
# 🔥 6️⃣ Retrieval
# =========================
def retrieve(query, k=5):
    query_vec = embed_model.encode([query])
    D, I = index.search(np.array(query_vec), k)
    return [documents[i] for i in I[0]]

# =========================
# 🔥 7️⃣ Chat memory
# =========================
chat_history = []

# =========================
# 首頁
# =========================
@app.route("/")
def home():
    return {"status": "RAG server running"}

# =========================
# 🔥 Chat API
# =========================
@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "")

    # ===== 記憶 =====
    chat_history.append(user_input)
    history_text = " ".join(chat_history[-3:])

    # ===== RAG =====
    context_list = retrieve(history_text)

    if not context_list:
        context_list = ["資料中未提及"]

    context = "\n".join(context_list)

    # 🔥 精簡 prompt（關鍵）
    prompt = f"""
請根據以下資料回答問題：

{context}

問題：{user_input}

規則：
1. 只回答重點（1~2句）
2. 不要重複問題
3. 如果資料沒有提到，回答「資料中未提及」
"""

    try:
        answer = generate_answer(prompt)
    except Exception as e:
        print("❌ LLM error:", e)
        answer = ""

    # fallback
    if not answer:
        answer = "資料中未提及"

    return jsonify({"reply": answer})


# =========================
# 啟動
# =========================
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)