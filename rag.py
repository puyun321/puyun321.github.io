# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 00:29:02 2026

@author: TKU
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
from bs4 import BeautifulSoup
from transformers import pipeline

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

os.environ["CUDA_VISIBLE_DEVICES"] = ""

app = Flask(__name__)
CORS(app)

# =========================
# 小 LLM
# =========================
llm = pipeline(
    "text-generation",
    model="google/flan-t5-small",
    device=-1
)

# =========================
# RAG storage
# =========================
chunks = []
vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = None

# =========================
# 🔥 Query Routing（核心）
# =========================
def route_query(query):
    q = query.lower()

    if "paper" in q or "publication" in q:
        return ["https://puyun321.github.io/Publication"]

    if "work" in q or "project" in q:
        return ["https://puyun321.github.io/Personal_work"]

    if "award" in q or "prize" in q:
        return ["https://puyun321.github.io/Academic_Award"]

    if "teaching" in q or "experience" in q:
        return ["https://puyun321.github.io/Teaching_Experience"]

    if "hobby" in q or "interest" in q:
        return ["https://puyun321.github.io/My_Hobbies"]

    return ["https://puyun321.github.io/"]

# =========================
# Clean HTML
# =========================
def extract_main_content(soup):
    main = soup.find("main")
    if main:
        return main.get_text(" ")

    article = soup.find("article")
    if article:
        return article.get_text(" ")

    for tag in soup(["nav", "footer", "header"]):
        tag.extract()

    return soup.get_text(" ")

# =========================
# Load website（支援 routing）
# =========================
def load_website(urls):
    texts = []

    for url in urls:
        try:
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")

            for t in soup(["script", "style"]):
                t.extract()

            text = extract_main_content(soup)

            words = text.split()
            words = [w for w in words if "@" not in w]

            texts.append(" ".join(words))

        except:
            pass

    return " ".join(texts)

# =========================
# Init RAG（動態）
# =========================
def init_rag(query):
    global chunks, tfidf_matrix

    print("🔄 Loading RAG...")

    urls = route_query(query)

    text = load_website(urls)
    words = text.split()

    chunks = []

    for i in range(0, len(words), 80):
        chunks.append(" ".join(words[i:i+80]))

    tfidf_matrix = vectorizer.fit_transform(chunks)

    print("✅ RAG ready!")

# =========================
# Retrieval
# =========================
def retrieve(query, top_k=3):
    query_vec = vectorizer.transform([query.lower()])
    scores = cosine_similarity(query_vec, tfidf_matrix)[0]
    top_idx = scores.argsort()[-top_k:][::-1]
    return [chunks[i] for i in top_idx]

# =========================
# Clean context
# =========================
def clean_context(text):
    words = text.split()

    blacklist = [
        "Home","Homepage","Profile","Contact","Email",
        "Back","More","Details","Support",
        "ResearchGate","Other","Personal",
        "Academic","Publications","Work"
    ]

    cleaned = [w for w in words if w not in blacklist]
    cleaned = [w for w in cleaned if "@" not in w]

    return " ".join(cleaned[:100])

# =========================
# 🔥 Paper Extraction
# =========================
def extract_publications(context, question):
    q = question.lower()

    if "paper" in q or "publication" in q:

        matches = re.findall(r"(20\d{2}[^.;\n]+)", context)

        unique = []
        for m in matches:
            if m not in unique:
                unique.append(m.strip())

        if len(unique) == 0:
            return None

        return unique[:5]

    return None

# =========================
# LLM（只處理一般問題）
# =========================
def call_llm(context, question):

    q = question.lower()

    if "name" in q:
        return "Kow Pu Yun"

    if "who" in q:
        return "AI professor at Tamkang University"

    prompt = f"""
Answer briefly.

Context:
{context[:150]}

Question:
{question}

Answer:
"""

    # try:
    #     res = llm(
    #         prompt,
    #         max_new_tokens=30,
    #         do_sample=False
    #     )

    #     ans = res[0]["generated_text"].strip()

    #     if len(ans) < 3:
    #         return context[:60]

    #     return ans

    # except:
    #     return context[:60]

    res = llm(
        prompt,
        max_new_tokens=100,
        do_sample=False
    )

    ans = res[0]["generated_text"].strip()

    if len(ans) < 3:
        return context[:60]

    return ans

# =========================
# API
# =========================
@app.route("/")
def home():
    return "Final RAG running"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        q = data.get("message", "")

        print("Q:", q)

        init_rag(q)

        docs = retrieve(q)
        context = clean_context(" ".join(docs))

        papers = extract_publications(context, q)

        if papers is not None:
            answer = "; ".join(papers)
        else:
            answer = call_llm(context, q)

        return jsonify({"reply": answer})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"reply": "error"})

# =========================
# Run
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)