import streamlit as st
import requests
import random
import time
import re
import json
import os
from collections import deque
from datetime import datetime

st.set_page_config(page_title="Intrinsic Motivation System", layout="wide")

STATE_FILE = "im_state.json"

class IntrinsicMotivationSystem:
    def __init__(self):
        self.knowledge = []          # thông tin đã thu
        self.goals = []              # mục tiêu dài hạn
        self.seen_tokens = deque(maxlen=200)
        self.action_log = []
        self.last_action_time = 0
        self.load()

    # ---------- Bộ nhớ ----------
    def remember(self, topic, content, source, novelty):
        content = content.strip()
        if len(content) < 20:
            return False
        # Tránh trùng
        for k in self.knowledge[-20:]:
            if k["topic"] == topic and content[:40] in k["content"]:
                return False
        self.knowledge.append({
            "topic": topic,
            "content": content[:500],
            "source": source,
            "novelty": novelty,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        self.save()
        return True

    def delete_knowledge(self, index):
        if 0 <= index < len(self.knowledge):
            self.knowledge.pop(index)
            self.save()

    # ---------- Tín hiệu tò mò ----------
    def compute_novelty(self, text):
        tokens = set(re.findall(r"[a-zA-Zà-ỹ0-9]{3,}", text.lower()))
        if not tokens:
            return 0.2
        overlap = len(tokens & set(self.seen_tokens))
        novelty = max(0.05, 1.0 - overlap / (len(tokens) + 5))
        self.seen_tokens.extend(list(tokens)[:8])
        return round(novelty, 2)

    # ---------- Mục tiêu ----------
    def add_goal(self, name, steps_needed=3):
        name = name.strip().lower()
        if not name or any(g["name"] == name for g in self.goals):
            return
        self.goals.append({
            "name": name,
            "needed": steps_needed,
            "done_steps": 0,
            "uncertainty": 1.0,
            "completed": False
        })
        self.save()

    def update_after_action(self, goal_name, novelty):
        for g in self.goals:
            if g["name"] == goal_name and not g["completed"]:
                g["done_steps"] += 1
                # Giảm uncertainty nhiều hơn nếu thông tin mới
                reduction = 0.3 * novelty
                g["uncertainty"] = max(0.05, g["uncertainty"] - reduction)
                if g["done_steps"] >= g["needed"] or g["uncertainty"] < 0.15:
                    g["completed"] = True
                self.save()
                return

    def select_goal(self):
        active = [g for g in self.goals if not g["completed"]]
        if not active:
            return None
        # Ưu tiên uncertainty cao nhất
        return max(active, key=lambda g: g["uncertainty"])["name"]

    def maybe_create_goal(self):
        if len([g for g in self.goals if not g["completed"]]) >= 4:
            return
        candidates = ["trí tuệ nhân tạo", "vật lý", "sinh học", "lịch sử", "công nghệ"]
        for c in candidates:
            if not any(g["name"] == c for g in self.goals):
                self.add_goal(c, steps_needed=2)
                self.log(f"Tự tạo mục tiêu: {c}")
                return

    # ---------- Hành động bên ngoài ----------
    def explore(self, topic):
        self.last_action_time = time.time()
        content, source = self._fetch(topic)
        if not content:
            self.log(f"Không tìm được thông tin về {topic}")
            return False, "Không có kết quả"

        novelty = self.compute_novelty(content)
        saved = self.remember(topic, content, source, novelty)
        self.update_after_action(topic, novelty if saved else 0.1)
        status = "Đã lưu" if saved else "Đã biết"
        self.log(f"{status} [{topic}] novelty={novelty}")
        return saved, f"{status} (novelty {novelty})"

    def _fetch(self, query):
        try:
            for lang in ["vi", "en"]:
                url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query.replace(' ', '_'))}"
                r = requests.get(url, timeout=8, headers={"User-Agent": "IM-System/1.0"})
                if r.status_code == 200:
                    data = r.json()
                    extract = data.get("extract", "")
                    if len(extract) > 40:
                        return extract[:450], f"wiki-{lang}"
        except Exception:
            pass
        return None, None

    def log(self, msg):
        self.action_log.append(f"{datetime.now().strftime('%H:%M:%S')} {msg}")
        self.action_log = self.action_log[-25:]
        self.save()

    def save(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "knowledge": self.knowledge,
                    "goals": self.goals,
                    "log": self.action_log
                }, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def load(self):
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                d = json.load(f)
                self.knowledge = d.get("knowledge", [])
                self.goals = d.get("goals", [])
                self.action_log = d.get("log", [])
        except Exception:
            pass

# ==================== APP ====================
if "system" not in st.session_state:
    st.session_state.system = IntrinsicMotivationSystem()
if "auto" not in st.session_state:
    st.session_state.auto = False

sys = st.session_state.system

st.title("Hệ thống Động lực Nội tại")

# Thanh trạng thái
active_goals = len([g for g in sys.goals if not g["completed"]])
st.write(f"Tri thức: {len(sys.knowledge)} | Mục tiêu đang theo: {active_goals} | Tự động: {'Bật' if st.session_state.auto else 'Tắt'}")

c1, c2 = st.columns(2)
with c1:
    if st.button("Tắt tự động" if st.session_state.auto else "Bật tự động", use_container_width=True):
        st.session_state.auto = not st.session_state.auto
        st.rerun()
with c2:
    if st.button("Xóa toàn bộ trạng thái", use_container_width=True):
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        st.session_state.system = IntrinsicMotivationSystem()
        st.session_state.auto = False
        st.rerun()

st.divider()

# Mục tiêu
st.subheader("Mục tiêu")
gc1, gc2 = st.columns([3, 1])
with gc1:
    g_input = st.text_input("Tên mục tiêu mới", label_visibility="collapsed", placeholder="Nhập mục tiêu...")
with gc2:
    if st.button("Thêm mục tiêu", use_container_width=True) and g_input.strip():
        sys.add_goal(g_input.strip())
        st.rerun()

if sys.goals:
    for g in sys.goals:
        status = "Hoàn thành" if g["completed"] else f"{g['done_steps']}/{g['needed']}"
        st.write(f"- {g['name']} | {status} | uncertainty: {g['uncertainty']:.2f}")
else:
    st.caption("Chưa có mục tiêu.")

# Hành động thủ công
st.subheader("Khám phá")
options = [g["name"] for g in sys.goals if not g["completed"]]
if not options:
    options = ["trí tuệ nhân tạo"]
selected = st.selectbox("Chọn chủ đề", options)
if st.button("Thực hiện khám phá", use_container_width=True):
    with st.spinner("Đang tìm kiếm..."):
        ok, msg = sys.explore(selected)
    if ok:
        st.success(msg)
    else:
        st.warning(msg)
    st.rerun()

# Tri thức
st.subheader("Tri thức đã thu")
if sys.knowledge:
    for i, k in enumerate(reversed(sys.knowledge[-12:])):
        real_idx = len(sys.knowledge) - 1 - i
        with st.expander(f"{k['topic']} ({k['source']}) novelty={k['novelty']} — {k['time']}"):
            st.write(k["content"])
            if st.button("Xóa mục này", key=f"rm_{real_idx}"):
                sys.delete_knowledge(real_idx)
                st.rerun()
else:
    st.info("Chưa có tri thức.")

# Log
if sys.action_log:
    with st.expander("Nhật ký hành động"):
        for line in reversed(sys.action_log[-8:]):
            st.text(line)

# Vòng tự động
if st.session_state.auto:
    sys.maybe_create_goal()
    if time.time() - sys.last_action_time > 20:
        goal = sys.select_goal()
        if goal:
            sys.explore(goal)
    time.sleep(2)
    st.rerun()
