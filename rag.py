# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from groq import Groq

app = Flask(__name__)
CORS(app)

groq_client = Groq()  # reads GROQ_API_KEY from env

chunks = []
vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = None


def route_query(query):
    q = query.lower()
    if any(w in q for w in ["paper", "publication", "research", "journal", "article", "study"]):
        return [("publication", "https://puyun321.github.io/Publication")]
    if any(w in q for w in ["work", "project", "application", "system", "develop"]):
        return [("work", "https://puyun321.github.io/Personal_work")]
    if any(w in q for w in ["award", "prize", "honor", "scholarship", "achievem"]):
        return [("award", "https://puyun321.github.io/Academic_Award")]
    if any(w in q for w in ["teach", "experience", "career", "job", "position", "professor"]):
        return [("teaching", "https://puyun321.github.io/Teaching_Experience")]
    if any(w in q for w in ["hobby", "interest", "travel", "leisure", "fun"]):
        return [("hobby", "https://puyun321.github.io/My_Hobbies")]
    return [("profile", "https://puyun321.github.io/")]


def load_pages(url_list):
    texts = []
    for tag, url in url_list:
        try:
            res = requests.get(url, timeout=8)
            soup = BeautifulSoup(res.text, "html.parser")
            for t in soup(["script", "style", "nav", "footer"]):
                t.extract()
            text = soup.get_text(separator=" ")
            text = re.sub(r'\S+@\S+', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            texts.append((tag, text))
        except Exception as e:
            print(f"Error loading {url}: {e}")
    return texts


def build_rag(query):
    global chunks, tfidf_matrix
    urls = route_query(query)
    page_texts = load_pages(urls)
    chunks = []
    for tag, text in page_texts:
        words = text.split()
        for i in range(0, len(words), 80):
            chunks.append((tag, " ".join(words[i:i + 80])))
    if chunks:
        tfidf_matrix = vectorizer.fit_transform([c[1] for c in chunks])


def retrieve(query, top_k=3):
    if tfidf_matrix is None or not chunks:
        return []
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, tfidf_matrix)[0]
    top_idx = scores.argsort()[-top_k:][::-1]
    return [chunks[i][1] for i in top_idx]


def call_llm(query, context):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=300,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for Kow Pu Yun's personal portfolio website. "
                    "Answer questions about Kow Pu Yun based ONLY on the provided context. "
                    "Be concise (2-4 sentences max). "
                    "If the context doesn't contain the answer, say so briefly."
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}"
            }
        ]
    )
    return response.choices[0].message.content


@app.route("/")
def home():
    return "RAG API running"


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        query = data.get("message", "").strip()

        if not query:
            return jsonify({"reply": "Please enter a question."})

        print(f"Query: {query}")

        build_rag(query)
        docs = retrieve(query)
        context = " ".join(docs)[:2000]

        answer = call_llm(query, context)

        return jsonify({"reply": answer})

    except Exception as e:
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            print("ERROR: Invalid GROQ_API_KEY")
            return jsonify({"reply": "API configuration error. Please contact the site owner."})
        print(f"ERROR: {e}")
        return jsonify({"reply": "Sorry, an error occurred. Please try again."})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
