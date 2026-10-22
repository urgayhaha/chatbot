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
        self.file_summaries = {}  # filename -> summary
        self.load()

    def add_entity(self, eid, etype="Unknown", props=None):
        eid = str(eid).strip().lower()
        if not eid or len(eid) < 2:
            return False
        if eid not in self.nodes:
            self.nodes[eid] = {"type": etype, "properties": props or {}, "created": time.time()}
            return True
        if props:
            self.nodes[eid].setdefault("properties", {}).update(props)
        return False

    def delete_node(self, nid):
        if nid in self.nodes:
            del self.nodes[nid]
            self.edges = [e for e in self.edges if e["source"] != nid and e["target"] != nid]
            self.save()
            return True
        return False

    def has_similar_info(self, about, content_preview):
        preview = content_preview[:70].lower().strip()
        if len(preview) < 15:
            return False
        for info in self.nodes.values():
            if info.get("type") != "Thông tin":
                continue
            p = info.get("properties", {})
            if p.get("about", "").lower() == about.lower():
                old = p.get("content", "")[:70].lower()
                if preview[:40] in old or old[:40] in preview:
                    return True
        return False

    def add_relation(self, src, tgt, rel, weight=1.0):
        src, tgt = str(src).strip().lower(), str(tgt).strip().lower()
        if not src or not tgt:
            return
        self.add_entity(src)
        self.add_entity(tgt)
        for e in self.edges:
            if e["source"] == src and e["target"] == tgt and e["relation"] == rel:
                return
        self.edges.append({"source": src, "target": tgt, "relation": rel, "weight": weight})

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({
                    "nodes": self.nodes,
                    "edges": self.edges,
                    "file_summaries": self.file_summaries
                }, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    d = json.load(f)
                    self.nodes = d.get("nodes", {})
                    self.edges = d.get("edges", [])
                    self.file_summaries = d.get("file_summaries", {})
            except:
                pass

# ==================== EXTRACTOR ====================
class Extractor:
    def __init__(self, mem):
        self.mem = mem

    def run(self, text):
        count = 0
        for sent in [s.strip() for s in re.split(r'[.\n;]', text) if len(s.strip()) > 4]:
            m = re.search(r"(.+?)\s+(là|sử dụng|dùng|tạo ra|mô phỏng)\s+(.+)", sent, re.I)
            if m:
                a, b = m.group(1).strip(), m.group(3).strip()
                if len(a) > 1 and len(b) > 1:
                    self.mem.add_entity(a, "Thực thể")
                    self.mem.add_entity(b, "Thực thể")
                    self.mem.add_relation(a, b, m.group(2))
                    count += 1
            else:
                if self.mem.add_entity(sent[:100], "Khái niệm"):
                    count += 1
        self.mem.save()
        return count

# ==================== CÔNG CỤ ====================
def wiki_search(q):
    try:
        for lang in ["vi", "en"]:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(str(q).replace(' ','_'))}",
                timeout=6, headers={"User-Agent": "AGI/1.0"}
            )
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
            a = r.json().get("AbstractText", "")
            if len(a) > 30:
                return a[:350]
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
                if len(t) > 15:
                    return t[:450]
            except:
                continue
    except:
        pass
    return ""

def summarize_file(filename, content):
    """Tóm tắt nội dung file bằng Gemini hoặc cắt đơn giản"""
    if len(content.strip()) < 30:
        return "Nội dung quá ngắn hoặc vô nghĩa."
    prompt = f"Tóm tắt ngắn gọn (3-5 câu) nội dung và ý nghĩa chính của văn bản sau bằng tiếng Việt:\n\n{content[:1500]}"
    summary = gemini_ask(prompt)
    if summary:
        return summary
    # Fallback
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    return " ".join(lines[:4])[:300] + ("..." if len(content) > 300 else "")

# ==================== ENGINE ====================
class Engine:
    def __init__(self, mem):
        self.mem = mem
        self.last = 0
        self.goals = []
        self.progress = {}
        self.uncertainty = {}
        self.searched = set()
        self.plan_queue = []  # hàng đợi bước kế hoạch

    def candidates(self):
        return [n for n, i in self.mem.nodes.items() if i.get("type") in ["Thực thể", "Khái niệm"]]

    def add_goal(self, name, need=3, auto=False):
        name = str(name).strip().lower()
        if not name or any(g["name"] == name for g in self.goals):
            return
        self.goals.append({"name": name, "need": need, "done": False, "auto": auto})
        self.progress[name] = 0
        self.uncertainty[name] = 1.0
        # Tạo kế hoạch đơn giản
        self.plan_queue.append({"goal": name, "step": "tìm định nghĩa"})
        self.plan_queue.append({"goal": name, "step": "tìm đặc điểm"})

    def auto_create_goals(self):
        """Tự tạo mục tiêu từ thực thể ít thông tin"""
        for c in self.candidates():
            info_count = sum(1 for i in self.mem.nodes.values()
                             if i.get("type") == "Thông tin" and i.get("properties", {}).get("about") == c)
            if info_count == 0 and c not in [g["name"] for g in self.goals] and len(self.goals) < 8:
                self.add_goal(c, need=2, auto=True)

    def explore(self, entity, force=False):
        entity = str(entity).strip().lower()
        if not force and entity in self.searched:
            return {"ok": False, "msg": "Đã khám phá"}

        self.last = time.time()
        self.searched.add(entity)

        results = []
        for src, func in [("Wiki", wiki_search), ("DDG", ddg_search)]:
            txt = func(entity)
            if txt and not self.mem.has_similar_info(entity, txt):
                results.append((src, txt))
        if not results and GEMINI_API_KEY:
            txt = gemini_ask(f"Giải thích ngắn bằng tiếng Việt: '{entity}' là gì?")
            if txt and not self.mem.has_similar_info(entity, txt):
                results.append(("Gemini", txt))

        if not results:
            return {"ok": False, "msg": "Không có thông tin mới"}

        src, txt = results[0]
        nid = f"info_{int(time.time()*1000)%1000000}"
        self.mem.add_entity(nid, "Thông tin", {"src": src, "content": txt, "about": entity})
        self.mem.add_relation(entity, nid, "có thông tin")
        self.mem.save()

        self.progress[entity] = self.progress.get(entity, 0) + 1
        self.uncertainty[entity] = max(0.05, self.uncertainty.get(entity, 1.0) - 0.22)

        for g in self.goals:
            if g["name"] == entity and self.progress.get(entity, 0) >= g["need"]:
                g["done"] = True

        return {"ok": True, "msg": f"{src}: {txt[:70]}", "unc": round(self.uncertainty.get(entity, 1), 2)}

    def auto_step(self):
        if time.time() - self.last < 9:
            return None
        self.auto_create_goals()
        # Thực hiện kế hoạch
        if self.plan_queue:
            step = self.plan_queue.pop(0)
            return self.explore(step["goal"])
        # Goal chưa xong
        for g in self.goals:
            if not g.get("done") and g["name"] not in self.searched:
                return self.explore(g["name"])
        return None

# ==================== KHỞI TẠO ====================
if "mem" not in st.session_state:
    st.session_state.mem = AGIMemory()
if "eng" not in st.session_state:
    st.session_state.eng = Engine(st.session_state.mem)
else:
    e = st.session_state.eng
    for attr, val in [("searched", set()), ("uncertainty", {}), ("progress", {}),
                      ("goals", []), ("plan_queue", [])]:
        if not hasattr(e, attr):
            setattr(e, attr, val)
if "running" not in st.session_state:
    st.session_state.running = False
if "logs" not in st.session_state:
    st.session_state.logs = []

mem = st.session_state.mem
eng = st.session_state.eng
extractor = Extractor(mem)

# ==================== UI ====================
st.title("🧠 AGI Cognitive Dashboard")

with st.sidebar:
    st.header("Điều khiển")
    if st.button("Dừng" if st.session_state.running else "Bật chạy ngầm", use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
    st.write("🟢 Đang chạy" if st.session_state.running else "🔴 Dừng")

    st.divider()
    st.subheader("Mục tiêu")
    gi = st.text_input("Thêm mục tiêu thủ công")
    if st.button("Thêm", use_container_width=True) and gi.strip():
        eng.add_goal(gi.strip())
        st.rerun()

    for g in eng.goals:
        n = g["name"]
        mark = "✅" if g.get("done") else f"{eng.progress.get(n,0)}/{g['need']}"
        auto_tag = " (tự)" if g.get("auto") else ""
        st.caption(f"{mark} {n}{auto_tag}")

    if st.session_state.logs:
        st.divider()
        for lg in reversed(st.session_state.logs[-4:]):
            st.caption(f"• {lg}")

t1, t2, t3, t4 = st.tabs(["Nhập liệu", "Thông tin", "File đã phân tích", "Khám phá"])

with t1:
    st.subheader("Nạp văn bản")
    txt = st.text_area("Văn bản", height=100)
    if st.button("Trích xuất", use_container_width=True) and txt.strip():
        st.success(f"Đã nạp {extractor.run(txt)} mục")
        st.rerun()

    st.divider()
    st.subheader("Tải file .txt lên")
    uploaded = st.file_uploader("Bấm để chọn file", type=["txt"], accept_multiple_files=True)
    if st.button("Đọc và phân tích file đã chọn", use_container_width=True):
        if uploaded:
            for uf in uploaded:
                raw = uf.read()
                path = os.path.join(KNOWLEDGE_FOLDER, uf.name)
                with open(path, "wb") as f:
                    f.write(raw)
                try:
                    text = raw.decode("utf-8", errors="ignore")
                    summary = summarize_file(uf.name, text)
                    mem.file_summaries[uf.name] = summary
                    extractor.run(text)
                    mem.save()
                    st.success(f"Đã phân tích: {uf.name}")
                except Exception as e:
                    st.warning(str(e))
            st.rerun()
        else:
            st.info("Chưa chọn file nào.")

with t2:
    c1, c2 = st.columns(2)
    c1.metric("Nodes", len(mem.nodes))
    c2.metric("Edges", len(mem.edges))

    infos = [(k, v) for k, v in mem.nodes.items() if v.get("type") == "Thông tin"]
    if infos:
        st.subheader("Thông tin đã thu thập")
        for k, v in reversed(infos):
            p = v.get("properties", {})
            col1, col2 = st.columns([5, 1])
            with col1:
                with st.expander(f"{p.get('about','?')} ← {p.get('src','')}"):
                    st.write(p.get("content", ""))
            with col2:
                if st.button("Xóa", key=f"del_{k}"):
                    mem.delete_node(k)
                    st.rerun()
    else:
        st.info("Chưa có thông tin.")

with t3:
    st.subheader("Tóm tắt file đã phân tích")
    if mem.file_summaries:
        for fname, summary in mem.file_summaries.items():
            with st.expander(f"📄 {fname}"):
                st.write(summary)
                if st.button(f"Xóa tóm tắt {fname}", key=f"del_sum_{fname}"):
                    del mem.file_summaries[fname]
                    mem.save()
                    st.rerun()
    else:
        st.info("Chưa có file nào được phân tích.")

with t4:
    cands = eng.candidates()
    if cands:
        sel = st.selectbox("Chọn thực thể", cands)
        if st.button("Khám phá", use_container_width=True):
            with st.spinner("..."):
                r = eng.explore(sel)
            if r.get("ok"):
                st.success(r["msg"])
                st.session_state.logs.append(f"{sel} → mới")
            else:
                st.info(r.get("msg"))
            st.rerun()
    else:
        st.info("Chưa có thực thể.")

if st.session_state.running:
    res = eng.auto_step()
    if res and res.get("ok"):
        st.toast(res["msg"][:50])
        st.session_state.logs.append(res["msg"][:35])
    time.sleep(8)
    st.rerun()
