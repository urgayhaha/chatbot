import streamlit as st
import numpy as np
import requests
import random
import time
import re
from collections import deque
from datetime import datetime

st.set_page_config(page_title="AGI News Agent", page_icon="🧠", layout="wide")

# ==================== BỘ NHỚ ====================
class Memory:
    def __init__(self):
        self.items = []  # {title, summary, source, time, about}

    def add(self, title, summary, source="news"):
        title = title.strip()
        if not title or self.exists(title):
            return False
        self.items.append({
            "title": title,
            "summary": summary[:500],
            "source": source,
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        return True

    def exists(self, title):
        t = title.lower()[:40]
        return any(t in x["title"].lower() for x in self.items[-30:])

    def recent(self, n=8):
        return list(reversed(self.items[-n:]))

# ==================== TÍN HIỆU TÒ MÒ ĐƠN GIẢN ====================
class Curiosity:
    def __init__(self):
        self.seen_topics = deque(maxlen=50)

    def score(self, text):
        words = set(re.findall(r"\w{4,}", text.lower()))
        overlap = len(words & set(self.seen_topics))
        novelty = max(0.1, 1.0 - overlap / 10.0)
        self.seen_topics.extend(list(words)[:5])
        return round(novelty, 2)

# ==================== TÌM TIN ====================
def fetch_news(query="tin tức mới"):
    """Lấy tin từ DuckDuckGo Instant Answer hoặc fallback"""
    results = []
    try:
        # Thử Wikipedia cho chủ đề
        url = f"https://vi.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query.replace(' ', '_'))}"
        r = requests.get(url, timeout=6, headers={"User-Agent": "AGI-Agent/1.0"})
        if r.status_code == 200:
            data = r.json()
            extract = data.get("extract", "")
            if len(extract) > 40:
                results.append({
                    "title": data.get("title", query),
                    "summary": extract[:400],
                    "source": "Wikipedia"
                })
    except:
        pass

    # Thêm tin mẫu nếu không có (để demo không trống)
    if not results:
        samples = [
            {"title": "AI tiếp tục phát triển", "summary": "Các mô hình ngôn ngữ lớn đang được cải thiện khả năng suy luận và sử dụng công cụ.", "source": "Demo"},
            {"title": "Công nghệ chip mới", "summary": "Nhà sản xuất công bố tiến trình nhỏ hơn giúp tăng hiệu năng và giảm điện năng.", "source": "Demo"},
        ]
        results.append(random.choice(samples))
    return results

def analyze(text):
    """Phân tích đơn giản: rút câu chính"""
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if len(s.strip()) > 20]
    if not sentences:
        return "Không đủ nội dung để phân tích."
    main = sentences[0]
    return f"Nội dung chính: {main}"

# ==================== KHỞI TẠO ====================
if "mem" not in st.session_state:
    st.session_state.mem = Memory()
if "cur" not in st.session_state:
    st.session_state.cur = Curiosity()
if "running" not in st.session_state:
    st.session_state.running = False
if "last_fetch" not in st.session_state:
    st.session_state.last_fetch = 0
if "log" not in st.session_state:
    st.session_state.log = []
if "goals" not in st.session_state:
    st.session_state.goals = ["tin tức AI", "công nghệ"]

mem = st.session_state.mem
cur = st.session_state.cur

# ==================== GIAO DIỆN ====================
st.title("🧠 AGI News Agent")
st.caption("Bộ nhớ + Tò mò + Tìm tin + Phân tích")

# Tiến độ thực tế hơn
st.write("**Tiến độ module**")
mods = [("Bộ nhớ", 70), ("Tín hiệu tò mò", 50), ("Tự kích hoạt", 60),
        ("Hành động tìm tin", 55), ("Phân tích", 40), ("Mục tiêu", 45)]
cols = st.columns(3)
for i, (name, pct) in enumerate(mods):
    with cols[i % 3]:
        st.metric(name, f"{pct}%")
        st.progress(pct / 100)

st.divider()

c1, c2 = st.columns(2)
with c1:
    if st.button("Dừng" if st.session_state.running else "Bật tìm tin tự động", use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
with c2:
    topic = st.text_input("Chủ đề tìm", value="AI")
    if st.button("Tìm ngay", use_container_width=True):
        news = fetch_news(topic)
        for n in news:
            score = cur.score(n["summary"])
            analysis = analyze(n["summary"])
            if mem.add(n["title"], n["summary"] + " | " + analysis, n["source"]):
                st.session_state.log.append(f"Mới: {n['title'][:40]} (tò mò {score})")
        st.rerun()

# Mục tiêu
st.write("**Mục tiêu hiện tại:**", ", ".join(st.session_state.goals))

# Kết quả
st.subheader("Tin đã thu thập")
recent = mem.recent(10)
if recent:
    for item in recent:
        with st.expander(f"{item['title']} — {item['source']} ({item['time']})"):
            st.write(item["summary"])
else:
    st.info("Chưa có tin. Bật tự động hoặc nhấn Tìm ngay.")

if st.session_state.log:
    st.caption("Nhật ký: " + " | ".join(st.session_state.log[-5:]))

# ==================== VÒNG TỰ ĐỘNG ====================
if st.session_state.running:
    now = time.time()
    # Khoảng 30 giây một lần (không phải 2 phút để demo nhanh hơn)
    if now - st.session_state.last_fetch > 30:
        st.session_state.last_fetch = now
        topic = random.choice(st.session_state.goals)
        news = fetch_news(topic)
        for n in news:
            score = cur.score(n["summary"])
            if score > 0.3:  # chỉ lấy nếu còn mới
                analysis = analyze(n["summary"])
                mem.add(n["title"], f"{n['summary']} | Phân tích: {analysis}", n["source"])
                st.session_state.log.append(f"{topic}: {n['title'][:30]}")
                if len(st.session_state.log) > 20:
                    st.session_state.log = st.session_state.log[-20:]
    time.sleep(2)
    st.rerun()
