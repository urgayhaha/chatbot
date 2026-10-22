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
        if not src or not tgt:
            return
        self.add_entity(src)
        self.add_entity(tgt)
        for e in self.edges:
            if e["source"] == src and e["target"] == tgt and e["relation"] == rel:
                e["weight"] = min(5.0, e.get("weight", 1) + 0.2)
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
                with open(self.path, encoding="utf-8") as f:
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
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(str(q).replace(' ','_'))}"
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
            abs_ = r.json().get("AbstractText", "")
            if len(abs_) > 30:
                return abs_[:350]
    except:
        pass
    return ""

def gemini_ask(prompt):
    if not GEMINI_API_KEY:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        for m in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                t = client.models.generate_content(model=m, contents=prompt).text.strip()
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
        self.uncertainty = {}
        self.source_quality = {"Wiki": 0.7, "DDG": 0.5, "Gemini": 0.6}
        self.knowledge = {}

    def candidates(self):
        return [n for n, i in self.mem.nodes.items() if i.get("type") not in ["Thông tin"]]

    def add_goal(self, name, need=3):
        name = str(name).strip().lower()
        if not name or any(g["name"] == name for g in self.goals):
            return
        self.goals.append({"name": name, "need": need, "done": False})
        self.progress[name] = 0
        self.uncertainty[name] = 1.0

    def is_duplicate(self, entity, new_text):
        olds = self.knowledge.get(entity, [])
        nt = new_text[:60].lower()
        for o in olds[-4:]:
            if nt in o.lower() or o[:60].lower() in new_text.lower():
                return True
        return False

    def update_source(self, src, useful):
        cur = self.source_quality.get(src, 0.5)
        if useful:
            self.source_quality[src] = min(0.92, cur + 0.04)
        else:
            self.source_quality[src] = max(0.25, cur - 0.06)

    def update_uncertainty(self, entity, quality, is_new):
        cur = self.uncertainty.get(entity, 1.0)
        q = quality if is_new else quality * 0.25
        count = len(self.knowledge.get(entity, []))
        factor = 0.28 / (1 + count * 0.12)
        self.uncertainty[entity] = max(0.04, cur - q * factor)

    def pick_target(self):
        active = [g for g in self.goals if not g.get("done")]
        if active:
            active.sort(key=lambda g: -self.uncertainty.get(g["name"], 0.5))
            return active[0]["name"]
        cands = self.candidates()
        if not cands:
            return None
        cands.sort(key=lambda x: -self.uncertainty.get(x, 0.75))
        return cands[0]

    def explore(self, entity):
        self.last = time.time()
        entity = str(entity).strip().lower()
        collected = []

        order = sorted(self.source_quality.items(), key=lambda x: -x[1])
        for src, _ in order:
            txt = ""
            if src == "Wiki":
                txt = wiki_search(entity)
            elif src == "DDG":
                txt = ddg_search(entity)
            elif src == "Gemini":
                txt = gemini_ask(f"Giải thích ngắn gọn bằng tiếng Việt về '{entity}'.")
            if txt and len(txt) > 25:
                collected.append((src, txt))

        if not collected:
            return {"ok": False, "msg": "Không tìm được thông tin"}

        best_src, best_txt = collected[0]
        dup = self.is_duplicate(entity, best_txt)

        nid = f"info_{int(time.time()) % 100000}"
        self.mem.add_entity(nid, "Thông tin", {"src": best_src, "content": best_txt, "about": entity})
        self.mem.add_relation(entity, nid, "có thông tin", weight=1.4)
        self.mem.save()

        self.knowledge.setdefault(entity, []).append(best_txt[:220])
        self.progress[entity] = self.progress.get(entity, 0) + 1
        q = self.source_quality.get(best_src, 0.5)
        self.update_uncertainty(entity, q, is_new=not dup)
        self.update_source(best_src, not dup)

        for g in self.goals:
            if g["name"] == entity and not g["done"]:
                if self.progress.get(entity, 0) >= g["need"] or self.uncertainty.get(entity, 1) < 0.22:
                    g["done"] = True

        return {
            "ok": True,
            "msg": f"{best_src}: {best_txt[:65]}",
            "unc": round(self.uncertainty.get(entity, 1), 2),
            "dup": dup
        }

    def auto_step(self):
        if time.time() - self.last < 8:
            return None
        t = self.pick_target()
        return self.explore(t) if t else None

# ==================== KHỞI TẠO ====================
if "mem" not in st.session_state:
    st.session_state.mem = AGIMemory()
if "eng" not in st.session_state:
    st.session_state.eng = Engine(st.session_state.mem)
else:
    e = st.session_state.eng
    for attr, default in [("uncertainty", {}), ("progress", {}), ("goals", []),
                          ("knowledge", {}), ("source_quality", {"Wiki": 0.7, "DDG": 0.5, "Gemini": 0.6}),
                          ("last", 0)]:
        if not hasattr(e, attr):
            setattr(e, attr, default)

if "running" not in st.session_state:
    st.session_state.running = False
if "logs" not in st.session_state:
    st.session_state.logs = []

mem = st.session_state.mem
eng = st.session_state.eng
extractor = Extractor(mem)

# ==================== UI ====================
st.title("🧠 AGI Cognitive Dashboard")
st.caption("Học từ kết quả + Mục tiêu + Giảm uncertainty")

with st.sidebar:
    st.header("Điều khiển")
    if st.button("Dừng" if st.session_state.running else "Bật chạy ngầm", use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
    st.write("🟢 Đang chạy" if st.session_state.running else "🔴 Dừng")

    st.divider()
    st.subheader("Mục tiêu")
    gname = st.text_input("Tên mục tiêu")
    if st.button("Thêm", use_container_width=True) and gname.strip():
        eng.add_goal(gname.strip())
        st.rerun()

    for g in eng.goals:
        n = g["name"]
        unc = eng.uncertainty.get(n, 1.0)
        p = eng.progress.get(n, 0)
        mark = "✅" if g.get("done") else f"{p}/{g['need']}"
        st.caption(f"{mark} {n} | unc: {unc:.2f}")

    if eng.source_quality:
        st.divider()
        st.caption("Chất lượng nguồn")
        for s, q in eng.source_quality.items():
            st.caption(f"{s}: {q:.2f}")

    if st.session_state.logs:
        st.divider()
        for lg in reversed(st.session_state.logs[-4:]):
            st.caption(f"• {lg}")

t1, t2, t3 = st.tabs(["Nhập liệu", "Thông tin", "Khám phá"])

with t1:
    txt = st.text_area("Văn bản", height=100)
    if st.button("Trích xuất") and txt.strip():
        st.success(f"Nạp {extractor.run(txt)} mục")
        st.rerun()
    ups = st.file_uploader("Upload .txt", type=["txt"], accept_multiple_files=True)
    if ups:
        for f in ups:
            open(os.path.join(KNOWLEDGE_FOLDER, f.name), "wb").write(f.read())
        st.rerun()

with t2:
    c1, c2 = st.columns(2)
    c1.metric("Nodes", len(mem.nodes))
    c2.metric("Edges", len(mem.edges))
    infos = [(k, v) for k, v in mem.nodes.items() if v.get("type") == "Thông tin"]
    for k, v in reversed(infos[-10:]):
        p = v.get("properties", {})
        with st.expander(f"{p.get('about','?')} ← {p.get('src','')}"):
            st.write(p.get("content", ""))

with t3:
    cands = eng.candidates()
    if cands:
        sel = st.selectbox("Thực thể", cands)
        if st.button("Khám phá", use_container_width=True):
            with st.spinner("Đang tìm..."):
                r = eng.explore(sel)
            if r.get("ok"):
                st.success(r["msg"])
                st.info(f"Uncertainty: {r.get('unc')} | Trùng: {r.get('dup')}")
                st.session_state.logs.append(f"{sel} → {r['msg'][:30]}")
                st.rerun()
            else:
                st.warning(r.get("msg"))
    else:
        st.info("Hãy nạp văn bản trước.")

if st.session_state.running:
    step = eng.auto_step()
    if step and step.get("ok"):
        st.toast(step["msg"][:50])
        st.session_state.logs.append(step["msg"][:40])
    time.sleep(7)
    st.rerun()
