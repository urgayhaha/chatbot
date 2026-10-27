# -*- coding: utf-8 -*-
"""
Nova Agent — Streamlit + Groq / Gemini (chạy trên Streamlit Cloud)

Secrets (Streamlit Cloud → Settings → Secrets):
GROQ_API_KEY = "gsk_..."
GEMINI_API_KEY = "AIza..."   # tùy chọn

Hoặc nhập key tạm trong sidebar.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

import streamlit as st

MEMORY_FILE = "memory.json"
MAX_HISTORY = 6


class Memory:
    def __init__(self, path=MEMORY_FILE):
        self.path = path
        self.items = []
        self.goals = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                self.items = data.get("items", [])
                self.goals = data.get("goals", [])
            except Exception:
                pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"items": self.items, "goals": self.goals}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_item(self, topic, content, source="chat"):
        content = str(content).strip()
        if len(content) < 8:
            return False
        preview = content[:40].lower()
        for it in self.items[-30:]:
            if preview in it.get("content", "").lower():
                return False
        self.items.append({
            "topic": topic[:60],
            "content": content[:500],
            "source": source,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        self.save()
        return True

    def add_goal(self, name):
        name = name.strip().lower()
        if name and not any(g["name"] == name for g in self.goals):
            self.goals.append({"name": name, "done": 0, "finished": False})
            self.save()

    def recall(self, keyword, limit=3):
        kw = keyword.strip().lower()
        if not kw:
            return []
        return [it for it in reversed(self.items)
                if kw in it.get("content", "").lower() or kw in it.get("topic", "").lower()][:limit]


def get_secret(name):
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def search_duckduckgo(query):
    try:
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
            "q": query, "format": "json", "no_html": "1", "skip_disambig": "1"
        })
        req = urllib.request.Request(url, headers={"User-Agent": "NovaAgent/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        abstract = data.get("AbstractText") or data.get("Abstract") or ""
        if len(abstract) > 40:
            return data.get("Heading") or query, abstract[:500], "duckduckgo"
        topics = data.get("RelatedTopics") or []
        texts = [t["Text"][:150] for t in topics[:3] if isinstance(t, dict) and t.get("Text")]
        if texts:
            return query, " | ".join(texts), "duckduckgo"
    except Exception:
        pass
    return None, None, None


def search_wiki(query):
    for lang in ("vi", "en"):
        try:
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ', '_'))}"
            req = urllib.request.Request(url, headers={"User-Agent": "NovaAgent/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            extract = data.get("extract", "")
            if len(extract) > 30:
                return data.get("title", query), extract[:400], f"wiki-{lang}"
        except Exception:
            continue
    return None, None, None


def call_groq(prompt, api_key):
    if not api_key:
        return "(Chưa có Groq API key)"
    try:
        import requests
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "max_tokens": 800
            },
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"(Groq lỗi {resp.status_code})"
    except Exception as e:
        return f"(Lỗi Groq: {e})"


def call_gemini(prompt, api_key):
    if not api_key:
        return "(Chưa có Gemini API key)"
    try:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        resp = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return f"(Gemini lỗi {resp.status_code})"
    except Exception as e:
        return f"(Lỗi Gemini: {e})"


def call_llm(prompt, provider, groq_key, gemini_key):
    if provider == "Groq":
        return call_groq(prompt, groq_key)
    return call_gemini(prompt, gemini_key)


def process_input(text, memory, history, provider, groq_key, gemini_key):
    text = text.strip()
    if not text:
        return ""
    lower = text.lower()

    if lower.startswith("nhớ ") or lower.startswith("lưu "):
        fact = text.split(" ", 1)[1]
        return "Đã lưu." if memory.add_item("user", fact) else "Không lưu được."

    if lower.startswith("mục tiêu ") or lower.startswith("goal "):
        g = text.split(" ", 1)[1]
        memory.add_goal(g)
        return f"Đã thêm mục tiêu: {g}"

    if lower.startswith("tìm ") or "wiki" in lower or "duck" in lower:
        q = re.sub(r"(tìm|wikipedia|wiki|duckduckgo|duck)", "", lower).strip() or text
        title, content, src = search_duckduckgo(q)
        if not content:
            title, content, src = search_wiki(q)
        if content:
            memory.add_item(q, content, src or "search")
            return f"[{src}] {title}:\n{content}"
        return "Không tìm thấy trên DuckDuckGo hoặc Wikipedia."

    recalled = memory.recall(text)
    mem_ctx = ""
    if recalled:
        mem_ctx = "\nĐã biết:\n" + "\n".join(f"- {r['content'][:100]}" for r in recalled)

    hist = "\n".join(f"{h['role']}: {h['text'][:80]}" for h in history[-MAX_HISTORY:])
    prompt = (
        "Bạn là Nova, trợ lý AI tiếng Việt. Trả lời ngắn, rõ, không bịa.\n"
        f"{mem_ctx}\nLịch sử:\n{hist}\nNgười dùng: {text}\nNova:"
    )
    return call_llm(prompt, provider, groq_key, gemini_key)


# ==================== UI ====================
st.set_page_config(page_title="Nova Agent", page_icon="🤖", layout="wide")
st.title("Nova Agent")

if "memory" not in st.session_state:
    st.session_state.memory = Memory()
if "history" not in st.session_state:
    st.session_state.history = []
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Cài đặt")
    provider = st.radio("LLM", ["Groq", "Gemini"], index=0)
    groq_key = st.text_input("Groq API Key", value=get_secret("GROQ_API_KEY"), type="password")
    gemini_key = st.text_input("Gemini API Key", value=get_secret("GEMINI_API_KEY"), type="password")
    st.caption("Key lấy miễn phí tại console.groq.com hoặc aistudio.google.com")
    st.divider()
    st.caption(f"Bộ nhớ: {len(st.session_state.memory.items)} mục")

with st.expander("Hướng dẫn"):
    st.markdown("""
- Hỏi bình thường để trò chuyện
- `nhớ ...` để lưu fact
- `mục tiêu ...` để thêm mục tiêu
- `tìm ...` để tìm DuckDuckGo rồi Wikipedia
- Nhập API key ở sidebar hoặc đặt trong Secrets
    """)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Nhập câu hỏi hoặc lệnh..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang xử lý..."):
            answer = process_input(
                prompt,
                st.session_state.memory,
                st.session_state.history,
                provider,
                groq_key,
                gemini_key
            )
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.history.append({"role": "user", "text": prompt})
    st.session_state.history.append({"role": "ai", "text": answer})
    if len(st.session_state.history) > 12:
        st.session_state.history = st.session_state.history[-12:]
    st.rerun()
