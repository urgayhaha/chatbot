import streamlit as st
import json
import os
import time
import re
import pandas as pd
import random
import requests
from datetime import datetime

st.set_page_config(page_title="AGI Cognitive Dashboard", page_icon="🧠", layout="wide")

GEMINI_API_KEY = "AQ.Ab8RN6I52wKSVq78IGjJl_zbSKfCVEgLDIEzhC_yES-ouv99KA"
KNOWLEDGE_FOLDER = "knowledge_files"
os.makedirs(KNOWLEDGE_FOLDER, exist_ok=True)

# ==================== 1. BỘ NHỚ ====================
class AGIKnowledgeMemory:
    def __init__(self, filepath="agi_long_term_memory.json"):
        self.filepath = filepath
        self.nodes = {}
        self.edges = []
        self.load_from_file()

    def add_entity(self, entity_id: str, entity_type: str, properties=None):
        entity_id = entity_id.strip().lower()
        if entity_id not in self.nodes:
            self.nodes[entity_id] = {
                "type": entity_type,
                "properties": properties or {},
                "created_at": time.time(),
                "updated_at": time.time()
            }
        else:
            if properties:
                self.nodes[entity_id]["properties"].update(properties)
            self.nodes[entity_id]["updated_at"] = time.time()

    def add_relation(self, source: str, target: str, relation: str, weight: float = 1.0):
        source = source.strip().lower()
        target = target.strip().lower()
        relation = relation.strip().lower()
        if source not in self.nodes: self.add_entity(source, "Unknown")
        if target not in self.nodes: self.add_entity(target, "Unknown")
        for edge in self.edges:
            if edge["source"] == source and edge["target"] == target and edge["relation"] == relation:
                edge["weight"] = min(5.0, edge["weight"] + 0.5)
                return
        self.edges.append({"source": source, "target": target, "relation": relation, "weight": weight, "created_at": time.time()})

    def save_to_file(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump({"nodes": self.nodes, "edges": self.edges}, f, indent=2, ensure_ascii=False)

    def load_from_file(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", [])

# ==================== 2. EXTRACTOR ====================
class AGIKnowledgeExtractor:
    def __init__(self, memory):
        self.memory = memory
        self.patterns = [
            (r"(.+?)\s+(là|bao gồm|thuộc về)\s+(.+)", "là"),
            (r"(.+?)\s+(sử dụng|dùng|áp dụng)\s+(.+)", "sử dụng"),
            (r"(.+?)\s+(phát triển|tạo ra|mô phỏng)\s+(.+)", "tạo ra"),
        ]

    def extract(self, text: str):
        count = 0
        for s in [x.strip() for x in re.split(r'[.\n;]', text) if x.strip()]:
            matched = False
            for pat, rel in self.patterns:
                m = re.search(pat, s, re.IGNORECASE)
                if m:
                    a, b = m.group(1).strip(), m.group(3).strip()
                    if len(a) > 1 and len(b) > 1:
                        self.memory.add_entity(a, "Thực thể")
                        self.memory.add_entity(b, "Thực thể")
                        self.memory.add_relation(a, b, rel)
                        count += 1
                        matched = True
                        break
            if not matched and len(s) > 1:
                self.memory.add_entity(s, "Khái niệm")
                count += 1
        self.memory.save_to_file()
        return count

# ==================== 3. CÔNG CỤ ====================
def search_wikipedia(q):
    headers = {"User-Agent": "AGI/1.0"}
    for lang, base in [("vi", "https://vi.wikipedia.org"), ("en", "https://en.wikipedia.org")]:
        try:
            r = requests.get(f"{base}/api/rest_v1/page/summary/{requests.utils.quote(q.replace(' ','_'))}", timeout=6, headers=headers)
            if r.status_code == 200:
                ext = r.json().get("extract", "")
                if len(ext) > 40:
                    return {"lang": lang, "extract": ext[:450]}
        except: pass
    return {}

def search_duckduckgo(q):
    try:
        r = requests.get("https://api.duckduckgo.com/", params={"q": q, "format": "json", "no_html": 1}, timeout=6, headers={"User-Agent": "AGI/1.0"})
        if r.status_code == 200:
            d = r.json()
            abs_ = d.get("AbstractText", "")
            if len(abs_) > 30: return abs_[:400]
            for t in d.get("RelatedTopics", [])[:2]:
                if isinstance(t, dict) and len(t.get("Text","")) > 30:
                    return t["Text"][:350]
    except: pass
    return ""

def call_gemini(prompt, key):
    if not key: return ""
    try:
        from google import genai
        client = genai.Client(api_key=key)
        for m in ["gemini-2.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash"]:
            try:
                t = client.models.generate_content(model=m, contents=prompt).text.strip()
                if len(t) > 15: return t[:500]
            except: continue
    except: pass
    return ""

def read_files():
    res = []
    if os.path.exists(KNOWLEDGE_FOLDER):
        for f in os.listdir(KNOWLEDGE_FOLDER):
            if f.endswith(".txt"):
                try:
                    with open(os.path.join(KNOWLEDGE_FOLDER, f), encoding="utf-8") as fh:
                        res.append({"file": f, "content": fh.read()[:600]})
                except: pass
    return res

# ==================== 4. ENGINE ====================
class CuriosityEngine:
    def __init__(self, memory):
        self.memory = memory
        self.last_time = 0
        self.goals = []
        self.progress = {}
        self.learned = {}

    def get_candidates(self):
        skip = ["Thông tin bên ngoài", "Phân tích AI", "Nội dung file"]
        return [n for n, i in self.memory.nodes.items() if i.get("type") not in skip]

    def add_goal(self, entity, target=3):
        entity = entity.strip().lower()
        if entity and entity not in [g["e"] for g in self.goals]:
            self.goals.append({"e": entity, "target": target, "status": "active"})
            self.progress[entity] = 0

    def learn(self, entity, content, source, score):
        self.learned.setdefault(entity, []).append({"c": content[:180], "src": source, "sc": score, "t": time.time()})
        if entity in self.progress:
            self.progress[entity] += 1
        for g in self.goals:
            if g["e"] == entity and g["status"] == "active" and self.progress.get(entity, 0) >= g["target"]:
                g["status"] = "done"

    def select_target(self):
        active = [g for g in self.goals if g["status"] == "active"]
        if active:
            active.sort(key=lambda g: self.progress.get(g["e"], 0))
            return active[0]["e"]
        c = self.get_candidates()
        return random.choice(c) if c else None

    def evaluate(self, t):
        if not t or len(t) < 25: return 0.2
        s = 0.5 + (0.2 if len(t) > 90 else 0) + (0.15 if any(k in t.lower() for k in ["là","được","có","is "]) else 0)
        return min(1.0, s)

    def explore(self, entity):
        self.last_time = time.time()
        results = []

        w = search_wikipedia(entity)
        if w:
            sc = self.evaluate(w["extract"])
            n = f"wiki_{int(time.time())%100000}"
            self.memory.add_entity(n, "Thông tin bên ngoài", {"source": f"wiki-{w['lang']}", "content": w["extract"], "about": entity, "u": round(sc,2)})
            self.memory.add_relation(entity, n, "từ wiki", weight=round(2+sc,1))
            results.append({"src": f"Wiki-{w['lang']}", "sc": sc, "pre": w["extract"][:80]})

        d = search_duckduckgo(entity)
        if d:
            sc = self.evaluate(d)
            n = f"ddg_{int(time.time())%100000}"
            self.memory.add_entity(n, "Thông tin bên ngoài", {"source": "ddg", "content": d, "about": entity, "u": round(sc,2)})
            self.memory.add_relation(entity, n, "từ ddg", weight=round(1.8+sc,1))
            results.append({"src": "DDG", "sc": sc, "pre": d[:80]})

        if GEMINI_API_KEY and max([r["sc"] for r in results], default=0) < 0.65:
            ai = call_gemini(f"Giải thích ngắn bằng tiếng Việt về '{entity}'.", GEMINI_API_KEY)
            if ai:
                sc = self.evaluate(ai)
                n = f"ai_{int(time.time())%100000}"
                self.memory.add_entity(n, "Phân tích AI", {"source": "gemini", "content": ai, "about": entity, "u": round(sc,2)})
                self.memory.add_relation(entity, n, "AI", weight=round(2+sc,1))
                results.append({"src": "Gemini", "sc": sc, "pre": ai[:80]})

        for f in read_files():
            if entity.lower() in f["content"].lower():
                n = f"file_{int(time.time())%100000}"
                self.memory.add_entity(n, "Nội dung file", {"source": f["file"], "content": f["content"][:350], "about": entity})
                self.memory.add_relation(entity, n, "trong file", weight=2.0)
                results.append({"src": f"File", "sc": 0.55, "pre": f["content"][:60]})
                break

        self.memory.save_to_file()
        if results:
            best = max(results, key=lambda x: x["sc"])
            self.learn(entity, best["pre"], best["src"], best["sc"])
            return {"ok": True, "target": entity, "detail": f"{len(results)} nguồn | {best['src']} ({best['sc']:.2f})", "results": results, "prog": self.progress.get(entity, 0)}
        return {"ok": False, "detail": "Không thu được"}

    def auto(self):
        if time.time() - self.last_time < 10: return {"ok": False}
        t = self.select_target()
        return self.explore(t) if t else {"ok": False}

    def goal_status(self):
        return [{"e": g["e"], "p": f"{self.progress.get(g['e'],0)}/{g['target']}", "st": g["status"], "kn": len(self.learned.get(g["e"], []))} for g in self.goals]

# ==================== 5. KHỞI TẠO ====================
if "mem" not in st.session_state:
    st.session_state.mem = AGIKnowledgeMemory()
if "run" not in st.session_state:
    st.session_state.run = False
if "eng" not in st.session_state:
    st.session_state.eng = CuriosityEngine(st.session_state.mem)
if "log" not in st.session_state:
    st.session_state.log = []

mem = st.session_state.mem
ext = AGIKnowledgeExtractor(mem)
eng = st.session_state.eng

# ==================== 6. UI ====================
st.title("🧠 AGI Dashboard")
st.caption("Mục tiêu dài hạn + Học từ kết quả")

st.sidebar.header("Điều khiển")
if st.sidebar.button("🛑 Dừng" if st.session_state.run else "🟢 Bật ngầm"):
    st.session_state.run = not st.session_state.run
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("Mục tiêu dài hạn")
ng = st.sidebar.text_input("Thêm mục tiêu")
if st.sidebar.button("➕ Thêm") and ng:
    eng.add_goal(ng)
    st.rerun()

for g in eng.goal_status():
    ic = "✅" if g["st"] == "done" else "🔄"
    st.sidebar.caption(f"{ic} {g['e']}: {g['p']} | {g['kn']} kt")

if st.session_state.log:
    st.sidebar.divider()
    for l in reversed(st.session_state.log[-4:]):
        st.sidebar.caption(f"• {l}")

t1, t2, t3 = st.tabs(["Nhập liệu", "Thông tin", "Khám phá"])

with t1:
    txt = st.text_area("Văn bản", "Mèo là động vật.\nAGI là trí tuệ nhân tạo.", height=70)
    if st.button("Trích xuất"):
        st.success(f"Nạp {ext.extract(txt)}")
        st.rerun()
    up = st.file_uploader("Upload .txt", type=["txt"], accept_multiple_files=True)
    if up:
        for f in up:
            open(os.path.join(KNOWLEDGE_FOLDER, f.name), "wb").write(f.getbuffer())
        st.rerun()

with t2:
    st.metric("Nodes", len(mem.nodes))
    infos = [(n,i) for n,i in mem.nodes.items() if i.get("type") in ["Thông tin bên ngoài","Phân tích AI","Nội dung file"]]
    for n, i in reversed(infos[-8:]):
        p = i.get("properties", {})
        with st.expander(f"[{p.get('source','')}] {p.get('about','')}"):
            st.write(p.get("content",""))

with t3:
    cands = eng.get_candidates()
    if cands:
        sel = st.selectbox("Thực thể", cands)
        if st.button("Khám phá"):
            with st.spinner("..."):
                r = eng.explore(sel)
            if r.get("ok"):
                st.success(r["detail"])
                st.session_state.log.append(f"{sel} → {r['detail']}")
                st.rerun()
            else:
                st.warning(r.get("detail"))
    else:
        st.info("Chưa có thực thể.")

if st.session_state.run:
    r = eng.auto()
    if r.get("ok"):
        st.toast(f"{r['target']} → {r['detail']}")
        st.session_state.log.append(f"{r['target']} → {r['detail']}")
    time.sleep(10)
    st.rerun()
