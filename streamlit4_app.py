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
        if not eid or len(eid) < 2:
            return False
        if eid not in self.nodes:
            self.nodes[eid] = {"type": etype, "properties": props or {}, "created": time.time()}
            return True
        if props:
            self.nodes[eid].setdefault("properties", {}).update(props)
        return False

    def has_similar_info(self, about, content_preview):
        """Kiểm tra đã có thông tin tương tự chưa"""
        preview = content_preview[:80].lower().strip()
        if len(preview) < 20:
            return False
        for nid, info in self.nodes.items():
            if info.get("type") != "Thông tin":
                continue
            p = info.get("properties", {})
            if p.get("about", "").lower() == about.lower():
                old = p.get("content", "")[:80].lower()
                if preview in old or old in preview or preview[:40] == old[:40]:
                    return True
        return False

    def add_relation(self, src, tgt, rel, weight=1.0):
        src = str(src).strip().lower()
        tgt = str(tgt).strip().lower()
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
        for sent in [s.strip() for s in re.split(r'[.\n;]', text) if len(s.strip()) > 3]:
            m = re.search(r"(.+?)\s+(là|sử dụng|dùng|tạo ra|mô phỏng)\s+(.+)", sent, re.I)
            if m:
                a, b = m.group(1).strip(), m.group(3).strip()
                if len(a) > 1 and len(b) > 1:
                    if self.mem.add_entity(a, "Thực thể"):
                        count += 1
                    if self.mem.add_entity(b, "Thực thể"):
                        count += 1
                    self.mem.add_relation(a, b, m.group(2))
            else:
                if self.mem.add_entity(sent[:80], "Khái niệm"):
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
                if len(ext) > 50:
                    return ext[:450]
    except:
        pass
    return ""

def ddg_search(q):
    try:
        r = requests.get("https://api.duckduckgo.com/", params={"q": q, "format": "json", "no_html": 1}, timeout=6)
        if r.status_code == 200:
            abs_ = r.json().get("AbstractText", "")
            if len(abs_) > 40:
                return abs_[:400]
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
                if len(t) > 20:
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
        self.searched = set()  # đã tìm rồi thì không tìm lại

    def candidates(self):
        return [n for n, i in self.mem.nodes.items() if i.get("type") in ["Thực thể", "Khái niệm", "Unknown"]]

    def add_goal(self, name, need=3):
        name = str(name).strip().lower()
        if not name or any(g["name"] == name for g in self.goals):
            return
        self.goals.append({"name": name, "need": need, "done": False})
        self.progress[name] = 0
        self.uncertainty[name] = 1.0

    def explore(self, entity, force=False):
        entity = str(entity).strip().lower()
        key = entity
        if not force and key in self.searched:
            return {"ok": False, "msg": "Đã khám phá trước đó, bỏ qua"}

        self.last = time.time()
        self.searched.add(key)

        collected = []
        for src in ["Wiki", "DDG", "Gemini"]:
            txt = ""
            if src == "Wiki":
                txt = wiki_search(entity)
            elif src == "DDG":
                txt = ddg_search(entity)
            elif src == "Gemini" and GEMINI_API_KEY:
                txt = gemini_ask(f"Giải thích ngắn bằng tiếng Việt về '{entity}'.")
            if txt and not self.mem.has_similar_info(entity, txt):
                collected.append((src, txt))

        if not collected:
            return {"ok": False, "msg": "Không có thông tin mới"}

        src, txt = collected[0]
        nid = f"info_{int(time.time()*1000) % 1000000}"
        self.mem.add_entity(nid, "Thông tin", {"src": src, "content": txt, "about": entity})
        self.mem.add_relation(entity, nid, "có thông tin")
        self.mem.save()

        self.progress[entity] = self.progress.get(entity, 0) + 1
        cur_unc = self.uncertainty.get(entity, 1.0)
        self.uncertainty[entity] = max(0.05, cur_unc - 0.2)

        for g in self.goals:
            if g["name"] == entity and self.progress.get(entity, 0) >= g["need"]:
                g["done"] = True

        return {"ok": True, "msg": f"{src}: {txt[:80]}", "unc": round(self.uncertainty.get(entity, 1), 2)}

    def auto_step(self):
        if time.time() - self.last < 10:
            return None
        # Ưu tiên goal chưa xong
        for g in self.goals:
            if not g.get("done") and g["name"] not in self.searched:
                return self.explore(g["name"])
        # Sau đó mới chọn candidate chưa tìm
        for c in self.candidates():
            if c not in self.searched:
                return self.explore(c)
        return None

# ==================== KHỞI TẠO ====================
if "mem" not in st.session_state:
    st.session_state.mem = AGIMemory()
if "eng" not in st.session_state:
    st.session_state.eng = Engine(st.session_state.mem)
else:
    e = st.session_state.eng
    if not hasattr(e, "searched"):
        e.searched = set()
    if not hasattr(e, "uncertainty"):
        e.uncertainty = {}
    if not hasattr(e, "progress"):
        e.progress = {}
    if not hasattr(e, "goals"):
        e.goals = []

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
    if st.button("Dừng chạy ngầm" if st.session_state.running else "Bật chạy ngầm", use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
    st.write("🟢 Đang chạy" if st.session_state.running else "🔴 Dừng")

    st.divider()
    st.subheader("Mục tiêu dài hạn")
    g_input = st.text_input("Tên mục tiêu", key="goal_in")
    if st.button("Thêm mục tiêu", use_container_width=True):
        if g_input.strip():
            eng.add_goal(g_input.strip())
            st.rerun()

    for g in eng.goals:
        n = g["name"]
        mark = "✅" if g.get("done") else f"{eng.progress.get(n,0)}/{g['need']}"
        unc = eng.uncertainty.get(n, 1.0)
        st.caption(f"{mark} {n} | unc {unc:.2f}")

    if st.session_state.logs:
        st.divider()
        st.caption("Nhật ký")
        for lg in reversed(st.session_state.logs[-5:]):
            st.caption(f"• {lg}")

tab1, tab2, tab3 = st.tabs(["Nhập liệu & File", "Thông tin đã có", "Khám phá"])

with tab1:
    st.subheader("Nạp văn bản")
    txt = st.text_area("Nội dung văn bản", height=120)
    if st.button("Trích xuất văn bản", use_container_width=True):
        if txt.strip():
            n = extractor.run(txt)
            st.success(f"Đã xử lý, thêm khoảng {n} mục mới")
            st.rerun()

    st.divider()
    st.subheader("Upload và đọc file .txt")
    uploaded_files = st.file_uploader(
        "Chọn file .txt để nạp vào bộ nhớ",
        type=["txt"],
        accept_multiple_files=True,
        key="file_uploader"
    )
    if uploaded_files:
        for uf in uploaded_files:
            # Lưu file
            save_path = os.path.join(KNOWLEDGE_FOLDER, uf.name)
            content_bytes = uf.read()
            with open(save_path, "wb") as f:
                f.write(content_bytes)
            # Đọc và nạp nội dung
            try:
                text_content = content_bytes.decode("utf-8", errors="ignore")
                added = extractor.run(text_content)
                st.success(f"Đã đọc '{uf.name}' và nạp {added} mục")
            except Exception as ex:
                st.warning(f"Lỗi đọc {uf.name}: {ex}")
        st.rerun()

    # Liệt kê file đã lưu
    try:
        saved = [f for f in os.listdir(KNOWLEDGE_FOLDER) if f.endswith(".txt")]
        if saved:
            st.caption("File đã lưu trong thư mục: " + ", ".join(saved))
    except:
        pass

with tab2:
    c1, c2 = st.columns(2)
    c1.metric("Tổng nodes", len(mem.nodes))
    c2.metric("Tổng edges", len(mem.edges))

    info_list = [(k, v) for k, v in mem.nodes.items() if v.get("type") == "Thông tin"]
    if info_list:
        st.subheader(f"Thông tin đã thu thập ({len(info_list)})")
        # Hiển thị nhiều hơn, không giới hạn cứng
        for k, v in reversed(info_list):
            p = v.get("properties", {})
            about = p.get("about", "?")
            src = p.get("src", "")
            content = p.get("content", "")
            with st.expander(f"**{about}** ← {src}", expanded=False):
                st.write(content)
                st.caption(f"ID: {k}")
    else:
        st.info("Chưa có thông tin bên ngoài nào.")

    # Hiển thị thực thể thường
    entities = [n for n, i in mem.nodes.items() if i.get("type") in ["Thực thể", "Khái niệm"]]
    if entities:
        st.subheader("Thực thể / Khái niệm")
        st.write(", ".join(entities[:30]) + ("..." if len(entities) > 30 else ""))

with tab3:
    cands = eng.candidates()
    if cands:
        selected = st.selectbox("Chọn thực thể để khám phá", options=cands)
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Khám phá (bỏ qua nếu đã tìm)", use_container_width=True):
                with st.spinner("Đang tìm..."):
                    res = eng.explore(selected, force=False)
                if res.get("ok"):
                    st.success(res["msg"])
                    st.session_state.logs.append(f"{selected} → mới")
                else:
                    st.info(res.get("msg", "Bỏ qua"))
                st.rerun()
        with col_b:
            if st.button("Tìm lại (bỏ qua kiểm tra trùng)", use_container_width=True):
                with st.spinner("Đang tìm lại..."):
                    res = eng.explore(selected, force=True)
                if res.get("ok"):
                    st.success(res["msg"])
                else:
                    st.warning(res.get("msg"))
                st.rerun()
    else:
        st.info("Chưa có thực thể. Hãy nạp văn bản hoặc upload file.")

# ==================== BACKGROUND ====================
if st.session_state.running:
    step_result = eng.auto_step()
    if step_result and step_result.get("ok"):
        st.toast(step_result["msg"][:55])
        st.session_state.logs.append(step_result["msg"][:40])
    time.sleep(8)
    st.rerun()
