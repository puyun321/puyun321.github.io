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

groq_client = None

def get_groq_client():
    global groq_client
    if groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        groq_client = Groq(api_key=api_key)
    return groq_client

chunks = []
page_full = []          # [(tag, full_text)] for the pages routed to this query
vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = None


PUB     = ("publication", "https://puyun321.github.io/Publication")
WORK    = ("work", "https://puyun321.github.io/Personal_work")
AWARD   = ("award", "https://puyun321.github.io/Academic_Award")
TEACH   = ("teaching", "https://puyun321.github.io/Teaching_Experience")
HOBBY   = ("hobby", "https://puyun321.github.io/My_Hobbies")
PROFILE = ("profile", "https://puyun321.github.io/")

# vague / opinion / overview questions — pull the substantive pages so the
# model has enough material to compare and give a thoughtful answer
BROAD_WORDS = [
    "interesting", "interest", "best", "favourite", "favorite", "impressive",
    "cool", "recommend", "highlight", "novel", "innovative", "proud", "most ",
    "compare", "difference", "overview", "summary", "summarise", "summarize",
    "tell me about", "who is", "background", "strength", "expertise", "focus",
    "why ", "opinion", "think", "厲害", "有趣", "推薦", "比較", "介紹",
]


def route_query(query):
    q = query.lower()
    pages = []

    def add(*items):
        for it in items:
            if it not in pages:
                pages.append(it)

    if any(w in q for w in ["paper", "publication", "research", "journal",
                            "article", "study", "model", "forecast", "論文", "研究"]):
        add(PUB)
    if any(w in q for w in ["work", "project", "application", "system",
                            "develop", "code", "github", "專案", "作品"]):
        add(WORK)
        # "work" is ambiguous (projects vs. employment) — include career page too
        if any(w in q for w in ["work", "now", "current", "where", "employ", "job"]):
            add(TEACH)
    if any(w in q for w in ["award", "prize", "honor", "scholarship",
                            "achievem", "recogni", "獎"]):
        add(AWARD)
    if any(w in q for w in ["teach", "experience", "career", "job", "position",
                            "professor", "lecturer", "employ", "工作", "經歷"]):
        add(TEACH)
    if any(w in q for w in ["hobby", "travel", "leisure", "fun", "興趣", "旅遊"]):
        add(HOBBY)

    if any(w in q for w in BROAD_WORDS):
        add(PUB, WORK, AWARD, PROFILE)

    if not pages:
        add(PROFILE, PUB)

    return pages


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
    global chunks, tfidf_matrix, page_full
    urls = route_query(query)
    page_texts = load_pages(urls)
    page_full = page_texts
    chunks = []
    for tag, text in page_texts:
        words = text.split()
        for i in range(0, len(words), 80):
            chunks.append((tag, " ".join(words[i:i + 80])))
    if chunks:
        tfidf_matrix = vectorizer.fit_transform([c[1] for c in chunks])
    return len(urls)


def retrieve(query, top_k=6):
    if tfidf_matrix is None or not chunks:
        return []
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, tfidf_matrix)[0]
    top_idx = scores.argsort()[-top_k:][::-1]
    return [chunks[i][1] for i in top_idx]


# Groq retired free-tier access to llama-3.3-70b-versatile (now enterprise-only),
# so try a list of models the standard API key can reach and use the first that
# works. Override the order with the GROQ_MODEL env var (comma-separated).
DEFAULT_MODELS = [
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
]


def get_models():
    env = os.environ.get("GROQ_MODEL", "").strip()
    if env:
        return [m.strip() for m in env.split(",") if m.strip()]
    return DEFAULT_MODELS


SYSTEM_PROMPT = (
    "You are Pu Yun's friendly AI guide on his personal portfolio website. "
    "Pu Yun (Kow Pu Yun / 邱普運) is a researcher in machine learning, deep "
    "learning, water resources, and environmental science.\n\n"
    "How to answer:\n"
    "- Ground answers in the provided context (publications, projects, awards, "
    "background). Prefer specifics: paper titles, methods, years.\n"
    "- You may go beyond a literal lookup: compare his projects, explain why a "
    "piece of research is novel or interesting, draw out themes across his work, "
    "and make reasonable inferences from the context.\n"
    "- If asked for an opinion (\"which research is most interesting?\", \"what is "
    "he best at?\"), give a thoughtful, engaging answer and briefly say why, "
    "based on the context. When the context lists several papers or projects, "
    "pick one or two and make the case for them — do not claim you lack "
    "information when a list is clearly present.\n"
    "- If the context genuinely lacks the answer, say so in one sentence, then "
    "share what you do know or suggest a related question.\n"
    "- Warm, conversational tone. Usually 2-6 sentences; use a short bullet list "
    "when comparing several items, but never markdown tables. End by inviting a "
    "follow-up when it fits.\n"
    "- Reply in the same language the visitor used (English or Traditional "
    "Chinese).\n"
    "- For questions unrelated to Pu Yun, answer briefly if harmless, then gently "
    "steer back to his work."
)


def call_llm(query, context, history=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for turn in (history or [])[-6:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content[:1500]})

    messages.append({
        "role": "user",
        "content": f"Context about Kow Pu Yun:\n{context}\n\nVisitor's question: {query}"
    })

    client = get_groq_client()
    last_error = None
    for model in get_models():
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=500,
                temperature=0.6,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            print(f"Model {model} failed: {type(e).__name__}: {e}")
    raise last_error


@app.route("/")
def home():
    return "RAG API running"


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True, silent=True) or {}
        query = (data.get("message") or "").strip()
        history = data.get("history") or []

        if not query:
            return jsonify({"reply": "Please enter a question."})

        print(f"Query: {query}")

        n_pages = build_rag(query)
        if n_pages >= 3:
            # broad / opinion question — give the model the whole set of routed
            # pages so it can compare across papers, projects and awards
            context = "\n\n".join(
                f"[{tag}]\n{text}" for tag, text in page_full
            )[:6000]
        else:
            docs = retrieve(query)
            context = " ".join(docs)[:3500]

        answer = call_llm(query, context, history)

        return jsonify({"reply": answer})

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return jsonify({"reply": f"Error: {type(e).__name__}: {str(e)[:200]}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
