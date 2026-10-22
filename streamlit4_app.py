import streamlit as st
import json
import os
import time
import re
import pandas as pd
import random
import requests

st.set_page_config(page_title="AGI Cognitive Dashboard", page_icon="🧠", layout="wide")

GEMINI_API_KEY = "AQ.Ab8RN6I52wKSVq78IGjJl_zbSKfCVEgLDIEzhC_yES-ouv99KA"
KNOWLEDGE_FOLDER = "knowledge_files"
os.makedirs(KNOWLEDGE_FOLDER, exist_ok=True)

# ==================== BỘ NHỚ ====================
class AGIMemory:
    def __init__(self, path="agi_memory.json"):
        self.path = path
        self.nodes = {}
        self.edges = []
        self.load()

    def add_entity(self, eid, etype="Unknown", props=None):
        eid = str(eid).strip().lower()
        if not eid:
            return
        if eid not in self.nodes:
            self.nodes[eid] = {"type": etype, "properties": props or {}, "created": time.time()}
        elif props:
            self.nodes[eid]["properties"].update(props)

    def add_relation(self, src, tgt, rel, weight=1.0):
        src, tgt, rel = src.strip().lower(), tgt.strip().lower(), rel.strip().lower()
        if not src or not tgt:
            return
        self.add_entity(src)
        self.add_entity(tgt)
        for e in self.edges:
            if e["source"] == src and e["target"] == tgt and e["relation"] == rel:
                e["weight"] = min(5.0, e["weight"] + 0.3)
                return
        self.edges.append({"source": src, "target": tgt, "relation": rel, "weight": weight})

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"nodes": self.nodes, "edges": self.edges}, f, ensure_ascii=False, indent=2)

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.nodes = d.get("nodes", {})
                    self.edges = d.get("edges", [])
            except:
                pass

# ==================== EXTRACTOR ====================
class Extractor:
    def __init__(self, mem):
        self.mem = mem

    def run(self, text):
        count = 0
        for sent in [s.strip() for s in re.split(r'[.\n;]', text) if s.strip()]:
            m = re.search(r"(.+?)\s+(là|sử dụng|dùng|tạo ra|mô phỏng)\s+(.+)", sent, re.I)
            if m and len(m.group(1)) > 1 and len(m.group(3)) > 1:
                self.mem.add_entity(m.group(1), "Thực thể")
                self.mem.add_entity(m.group(3), "Thực thể")
                self.mem.add_relation(m.group(1), m.group(3), m.group(2))
                count += 1
            elif len(sent) > 2:
                self.mem.add_entity(sent, "Khái niệm")
                count += 1
        self.mem.save()
        return count

# ==================== CÔNG CỤ ====================
def wiki_search(q):
    try:
        for lang in ["vi", "en"]:
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(q.replace(' ','_'))}"
            r = requests.get(url, timeout=6, headers={"User-Agent": "AGI/1.0"})
            if r.status_code == 200:
                ext = r.json().get("extract", "")
                if len(ext) > 40:
                    return ext[:400]
    except:
        pass
    return ""

def ddg_search(q):
    try:
        r = requests.get("https://api.duckduckgo.com/", params={"q": q, "format": "json", "no_html": 1}, timeout=6)
        if r.status_code == 200:
            d = r.json()
            if len(d.get("AbstractText", "")) > 30:
                return d["AbstractText"][:350]
    except:
        pass
    return ""

def gemini_ask(prompt):
    if not GEMINI_API_KEY:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        for model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                t = client.models.generate_content(model=model, contents=prompt).text.strip()
                if len(t) > 10:
                    return t[:400]
            except:
                continue
    except:
        pass
    return ""

# ==================== ENGINE ====================
class Engine:
    def __init__(self, mem):
        self.mem = mem
        self.last = 0
        self.goals = []
        self.progress = {}
        self.uncertainty = {}  # entity -> điểm không chắc chắn (cao = chưa rõ)

    def candidates(self):
        skip = ["Thông tin", "AI", "File"]
        return [n for n, i in self.mem.nodes.items() if i.get("type") not in skip]

    def add_goal(self, name, need=3):
        name = name.strip().lower()
        if name and name not in [g["name"] for g in self.goals]:
            self.goals.append({"name": name, "need": need, "done": False})
            self.progress[name] = 0
            self.uncertainty[name] = 1.0

    def update_uncertainty(self, entity, info_quality):
        """Giảm sự không chắc chắn khi có thông tin tốt"""
        cur = self.uncertainty.get(entity, 1.0)
        reduction = info_quality * 0.25
        self.uncertainty[entity] = max(0.05, cur - reduction)

    def pick_target(self):
        # Ưu tiên mục tiêu chưa xong có uncertainty cao
        active = [g for g in self.goals if not g["done"]]
        if active:
            active.sort(key=lambda g: -self.uncertainty.get(g["name"], 0.5))
            return active[0]["name"]
        c = self.candidates()
        if not c:
            return None
        # Chọn node có uncertainty cao nhất
        c.sort(key=lambda x: -self.uncertainty.get(x, 0.8))
        return c[0]

    def explore(self, entity):
        self.last = time.time()
        infos = []

        w = wiki_search(entity)
        if w:
            infos.append(("Wiki", w, 0.7))
        d = ddg_search(entity)
        if d:
            infos.append(("DDG", d, 0.55))
        if GEMINI_API_KEY and len(infos) < 2:
            g = gemini_ask(f"Giải thích ngắn về '{entity}' bằng tiếng Việt.")
            if g:
                infos.append(("Gemini", g, 0.65))

        if not infos:
            return {"ok": False, "msg": "Không tìm được thông tin"}

        best_src, best_txt, best_q = max(infos, key=lambda x: x[2])
        node = f"info_{int(time.time()) % 100000}"
        self.mem.add_entity(node, "Thông tin", {"src": best_src, "content": best_txt, "about": entity})
        self.mem.add_relation(entity, node, "có thông tin", weight=1.5 + best_q)
        self.mem.save()

        # Học + giảm uncertainty
        self.progress[entity] = self.progress.get(entity, 0) + 1
        self.update_uncertainty(entity, best_q)

        for g in self.goals:
            if g["name"] == entity and not g["done"] and self.progress.get(entity, 0) >= g["need"]:
                g["done"] = True

        return {"ok": True, "msg": f"{best_src}: {best_txt[:60]}...", "unc": round(self.uncertainty.get(entity, 1), 2)}

    def auto_step(self):
        if time.time() - self.last < 8:
            return None
        t = self.pick_target()
        if not t:
            return None
        return self.explore(t)

# ==================== KHỞI TẠO ====================
if "mem" not in st.session_state:
    st.session_state.mem = AGIMemory()
if "eng" not in st.session_state:
    st.session_state.eng = Engine(st.session_state.mem)
if "running" not in st.session_state:
    st.session_state.running = False
if "logs" not in st.session_state:
    st.session_state.logs = []

mem = st.session_state.mem
eng = st.session_state.eng
extractor = Extractor(mem)

# ==================== GIAO DIỆN ====================
st.title("🧠 AGI Cognitive Dashboard")

# Sidebar
with st.sidebar:
    st.header("Điều khiển")
    if st.button("Dừng chạy ngầm" if st.session_state.running else "Bật chạy ngầm", use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
    st.write("Trạng thái:", "🟢 Đang chạy" if st.session_state.running else "🔴 Dừng")

    st.divider()
    st.subheader("Mục tiêu dài hạn")
    goal_input = st.text_input("Tên mục tiêu")
    if st.button("Thêm mục tiêu", use_container_width=True):
        if goal_input.strip():
            eng.add_goal(goal_input.strip())
            st.success(f"Đã thêm: {goal_input}")
            st.rerun()

    if eng.goals:
        for g in eng.goals:
            unc = eng.uncertainty.get(g["name"], 1.0)
            prog = eng.progress.get(g["name"], 0)
            status = "✅" if g["done"] else f"{prog}/{g['need']}"
            st.caption(f"{status} {g['name']} | không chắc: {unc:.2f}")

    if st.session_state.logs:
        st.divider()
        st.caption("Nhật ký")
        for lg in reversed(st.session_state.logs[-5:]):
            st.caption(f"• {lg}")

# Tabs
tab1, tab2, tab3 = st.tabs(["Nhập liệu", "Thông tin", "Khám phá"])

with tab1:
    st.subheader("Nạp văn bản")
    txt = st.text_area("Nội dung", height=100)
    if st.button("Trích xuất vào bộ nhớ"):
        if txt.strip():
            n = extractor.run(txt)
            st.success(f"Đã nạp {n} mục")
            st.rerun()

    st.divider()
    st.subheader("Upload file .txt")
    files = st.file_uploader("Chọn file", type=["txt"], accept_multiple_files=True)
    if files:
        for f in files:
            save_path = os.path.join(KNOWLEDGE_FOLDER, f.name)
            with open(save_path, "wb") as out:
                out.write(f.read())
            st.success(f"Đã lưu {f.name}")
        st.rerun()

    existing = [f for f in os.listdir(KNOWLEDGE_FOLDER) if f.endswith(".txt")]
    if existing:
        st.caption("File đã có: " + ", ".join(existing))

with tab2:
    st.metric("Số thực thể", len(mem.nodes))
    st.metric("Số quan hệ", len(mem.edges))
    infos = [(k, v) for k, v in mem.nodes.items() if v.get("type") == "Thông tin"]
    if infos:
        st.subheader("Thông tin đã thu thập")
        for k, v in reversed(infos[-10:]):
            p = v.get("properties", {})
            with st.expander(f"{p.get('about', '?')} ← {p.get('src', '')}"):
                st.write(p.get("content", ""))

with tab3:
    cands = eng.candidates()
    if cands:
        choice = st.selectbox("Chọn để khám phá", cands)
        if st.button("Khám phá ngay", use_container_width=True):
            with st.spinner("Đang tìm..."):
                res = eng.explore(choice)
            if res.get("ok"):
                st.success(res["msg"])
                st.info(f"Độ không chắc chắn còn lại: {res.get('unc', '?')}")
                st.session_state.logs.append(f"{choice} → {res['msg'][:40]}")
                st.rerun()
            else:
                st.warning(res.get("msg", "Thất bại"))
    else:
        st.info("Chưa có thực thể. Hãy nạp văn bản trước.")

# Background
if st.session_state.running:
    result = eng.auto_step()
    if result and result.get("ok"):
        st.toast(result["msg"][:50])
        st.session_state.logs.append(result["msg"][:40])
    time.sleep(6)
    st.rerun()
