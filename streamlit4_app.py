import streamlit as st
import json
import os
import time
import re
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
            self.nodes[eid].setdefault("properties", {}).update(props)

    def add_relation(self, src, tgt, rel, weight=1.0):
        src = str(src).strip().lower()
        tgt = str(tgt).strip().lower()
        rel = str(rel).strip().lower()
        if not src or not tgt:
            return
        self.add_entity(src)
        self.add_entity(tgt)
        for e in self.edges:
            if e["source"] == src and e["target"] == tgt and e["relation"] == rel:
                e["weight"] = min(5.0, e.get("weight", 1) + 0.3)
                return
        self.edges.append({"source": src, "target": tgt, "relation": rel, "weight": weight})

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"nodes": self.nodes, "edges": self.edges}, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.nodes = d.get("nodes", {})
                    self.edges = d.get("edges", [])
            except:
                self.nodes = {}
                self.edges = []

# ==================== EXTRACTOR ====================
class Extractor:
    def __init__(self, mem):
        self.mem = mem

    def run(self, text):
        count = 0
        for sent in [s.strip() for s in re.split(r'[.\n;]', text) if s.strip()]:
            m = re.search(r"(.+?)\s+(là|sử dụng|dùng|tạo ra|mô phỏng)\s+(.+)", sent, re.I)
            if m and len(m.group(1).strip()) > 1 and len(m.group(3).strip()) > 1:
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
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(str(q).replace(' ', '_'))}"
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
            abstract = r.json().get("AbstractText", "")
            if len(abstract) > 30:
                return abstract[:350]
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
                text = client.models.generate_content(model=model, contents=prompt).text.strip()
                if len(text) > 10:
                    return text[:400]
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
        self.uncertainty = {}

    def candidates(self):
        return [n for n, i in self.mem.nodes.items() if i.get("type") not in ["Thông tin", "AI", "File"]]

    def add_goal(self, name, need=3):
        name = str(name).strip().lower()
        if not name:
            return
        if name not in [g["name"] for g in self.goals]:
            self.goals.append({"name": name, "need": int(need), "done": False})
            self.progress[name] = 0
            self.uncertainty[name] = 1.0

    def update_uncertainty(self, entity, quality):
        cur = self.uncertainty.get(entity, 1.0)
        self.uncertainty[entity] = max(0.05, cur - quality * 0.25)

    def pick_target(self):
        active = [g for g in self.goals if not g.get("done")]
        if active:
            active.sort(key=lambda g: -self.uncertainty.get(g["name"], 0.5))
            return active[0]["name"]
        cands = self.candidates()
        if not cands:
            return None
        cands.sort(key=lambda x: -self.uncertainty.get(x, 0.8))
        return cands[0]

    def explore(self, entity):
        self.last = time.time()
        entity = str(entity).strip().lower()
        infos = []

        w = wiki_search(entity)
        if w:
            infos.append(("Wiki", w, 0.7))
        d = ddg_search(entity)
        if d:
            infos.append(("DDG", d, 0.55))
        if len(infos) < 2:
            g = gemini_ask(f"Giải thích ngắn về '{entity}' bằng tiếng Việt.")
            if g:
                infos.append(("Gemini", g, 0.65))

        if not infos:
            return {"ok": False, "msg": "Không tìm được thông tin"}

        src, txt, q = max(infos, key=lambda x: x[2])
        node_id = f"info_{int(time.time()) % 100000}"
        self.mem.add_entity(node_id, "Thông tin", {"src": src, "content": txt, "about": entity})
        self.mem.add_relation(entity, node_id, "có thông tin", weight=1.5 + q)
        self.mem.save()

        self.progress[entity] = self.progress.get(entity, 0) + 1
        self.update_uncertainty(entity, q)

        for g in self.goals:
            if g["name"] == entity and not g["done"] and self.progress.get(entity, 0) >= g["need"]:
                g["done"] = True

        return {"ok": True, "msg": f"{src}: {txt[:70]}", "unc": round(self.uncertainty.get(entity, 1.0), 2)}

    def auto_step(self):
        if time.time() - self.last < 8:
            return None
        target = self.pick_target()
        if not target:
            return None
        return self.explore(target)

# ==================== KHỞI TẠO AN TOÀN ====================
if "mem" not in st.session_state:
    st.session_state.mem = AGIMemory()

if "eng" not in st.session_state:
    st.session_state.eng = Engine(st.session_state.mem)
else:
    # Đảm bảo thuộc tính tồn tại nếu object cũ
    eng_tmp = st.session_state.eng
    if not hasattr(eng_tmp, "uncertainty"):
        eng_tmp.uncertainty = {}
    if not hasattr(eng_tmp, "progress"):
        eng_tmp.progress = {}
    if not hasattr(eng_tmp, "goals"):
        eng_tmp.goals = []
    if not hasattr(eng_tmp, "last"):
        eng_tmp.last = 0

if "running" not in st.session_state:
    st.session_state.running = False
if "logs" not in st.session_state:
    st.session_state.logs = []

mem = st.session_state.mem
eng = st.session_state.eng
extractor = Extractor(mem)

# ==================== GIAO DIỆN ====================
st.title("🧠 AGI Cognitive Dashboard")

with st.sidebar:
    st.header("Điều khiển")
    label = "Dừng chạy ngầm" if st.session_state.running else "Bật chạy ngầm"
    if st.button(label, use_container_width=True, key="btn_run"):
        st.session_state.running = not st.session_state.running
        st.rerun()
    st.write("Trạng thái:", "🟢 Đang chạy" if st.session_state.running else "🔴 Dừng")

    st.divider()
    st.subheader("Mục tiêu dài hạn")
    goal_name = st.text_input("Tên mục tiêu", key="goal_input")
    if st.button("Thêm mục tiêu", use_container_width=True, key="btn_goal"):
        if goal_name and goal_name.strip():
            eng.add_goal(goal_name.strip())
            st.success("Đã thêm")
            st.rerun()

    if eng.goals:
        for g in eng.goals:
            name = g.get("name", "?")
            unc = eng.uncertainty.get(name, 1.0)
            prog = eng.progress.get(name, 0)
            need = g.get("need", 3)
            mark = "✅" if g.get("done") else f"{prog}/{need}"
            st.caption(f"{mark} {name} | không chắc: {unc:.2f}")

    if st.session_state.logs:
        st.divider()
        st.caption("Nhật ký gần nhất")
        for item in reversed(st.session_state.logs[-5:]):
            st.caption(f"• {item}")

tab1, tab2, tab3 = st.tabs(["Nhập liệu", "Thông tin", "Khám phá"])

with tab1:
    st.subheader("Nạp văn bản")
    text_in = st.text_area("Nội dung", height=120, key="text_area")
    if st.button("Trích xuất vào bộ nhớ", key="btn_extract"):
        if text_in and text_in.strip():
            n = extractor.run(text_in)
            st.success(f"Đã nạp {n} mục")
            st.rerun()

    st.divider()
    st.subheader("Upload file .txt")
    uploaded = st.file_uploader("Chọn một hoặc nhiều file", type=["txt"], accept_multiple_files=True, key="uploader")
    if uploaded:
        for uf in uploaded:
            path = os.path.join(KNOWLEDGE_FOLDER, uf.name)
            with open(path, "wb") as f:
                f.write(uf.read())
            st.success(f"Đã lưu: {uf.name}")

    try:
        existing_files = [f for f in os.listdir(KNOWLEDGE_FOLDER) if f.endswith(".txt")]
        if existing_files:
            st.caption("File trong thư mục: " + ", ".join(existing_files))
    except:
        pass

with tab2:
    col1, col2 = st.columns(2)
    col1.metric("Thực thể", len(mem.nodes))
    col2.metric("Quan hệ", len(mem.edges))

    info_nodes = [(k, v) for k, v in mem.nodes.items() if v.get("type") == "Thông tin"]
    if info_nodes:
        st.subheader("Thông tin đã thu thập")
        for k, v in list(reversed(info_nodes))[:12]:
            props = v.get("properties", {})
            title = f"{props.get('about', '?')}  ←  {props.get('src', '')}"
            with st.expander(title):
                st.write(props.get("content", "(không có nội dung)"))

with tab3:
    cands = eng.candidates()
    if cands:
        selected = st.selectbox("Chọn thực thể", cands, key="sel_entity")
        if st.button("Khám phá ngay", use_container_width=True, key="btn_explore"):
            with st.spinner("Đang tìm thông tin..."):
                result = eng.explore(selected)
            if result.get("ok"):
                st.success(result["msg"])
                st.info(f"Độ không chắc chắn còn lại: {result.get('unc', '?')}")
                st.session_state.logs.append(f"{selected} → ok")
                st.rerun()
            else:
                st.warning(result.get("msg", "Không thành công"))
    else:
        st.info("Chưa có thực thể nào. Hãy nạp văn bản ở tab Nhập liệu.")

# ==================== BACKGROUND ====================
if st.session_state.running:
    step = eng.auto_step()
    if step and step.get("ok"):
        st.toast(step["msg"][:60])
        st.session_state.logs.append(step["msg"][:50])
    time.sleep(7)
    st.rerun()
