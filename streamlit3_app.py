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

# ==================== CẤU HÌNH API ====================
GEMINI_API_KEY = "AQ.Ab8RN6I52wKSVq78IGjJl_zbSKfCVEgLDIEzhC_yES-ouv99KA"
GOOGLE_API_KEY = ""      # Điền Google Custom Search API Key
GOOGLE_CX = ""           # Điền Search Engine ID (cx)

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
        if source not in self.nodes:
            self.add_entity(source, "Unknown")
        if target not in self.nodes:
            self.add_entity(target, "Unknown")
        for edge in self.edges:
            if edge["source"] == source and edge["target"] == target and edge["relation"] == relation:
                edge["weight"] = min(5.0, edge["weight"] + 0.5)
                return
        self.edges.append({
            "source": source, "target": target, "relation": relation,
            "weight": weight, "created_at": time.time()
        })

    def save_to_file(self):
        data = {"nodes": self.nodes, "edges": self.edges,
                "meta": {"total_nodes": len(self.nodes), "total_edges": len(self.edges), "saved_at": time.time()}}
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", [])

# ==================== 2. EXTRACTOR ====================
class AGIKnowledgeExtractor:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.relation_patterns = [
            (r"(.+?)\s+(là|bao gồm|được phân loại là|thuộc về)\s+(.+)", "là / thuộc về"),
            (r"(.+?)\s+(sử dụng|áp dụng|dùng|vận hành bằng)\s+(.+)", "sử dụng"),
            (r"(.+?)\s+(phát triển|tạo ra|nghiên cứu|mô phỏng)\s+(.+)", "tạo ra / mô phỏng"),
            (r"(.+?)\s+(kết nối với|liên kết với|tương tác với)\s+(.+)", "kết nối với"),
        ]

    def extract_and_ingest(self, text: str):
        sentences = [s.strip() for s in re.split(r'[.\n;]', text) if s.strip()]
        count = 0
        for sentence in sentences:
            matched = False
            for pattern, rel in self.relation_patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    sub = re.sub(r'^(một|các|những|hệ thống|mô hình)\s+', '', match.group(1).strip(), flags=re.IGNORECASE)
                    obj = re.sub(r'^(một|các|những|hệ thống|mô hình)\s+', '', match.group(3).strip(), flags=re.IGNORECASE)
                    if len(sub) >= 2 and len(obj) >= 2:
                        self.memory.add_entity(sub, "Thực thể chính")
                        self.memory.add_entity(obj, "Thực thể chính")
                        self.memory.add_relation(sub, obj, rel)
                        count += 1
                        matched = True
                        break
            if not matched and len(sentence.strip()) >= 2:
                self.memory.add_entity(sentence.strip(), "Khái niệm thô")
                count += 1
        self.memory.save_to_file()
        return count

# ==================== 3. CÔNG CỤ BÊN NGOÀI ====================
def search_wikipedia(query: str) -> dict:
    headers = {"User-Agent": "AGI-Dashboard/1.0"}
    for lang, base in [("vi", "https://vi.wikipedia.org"), ("en", "https://en.wikipedia.org")]:
        try:
            url = f"{base}/api/rest_v1/page/summary/{requests.utils.quote(query.replace(' ', '_'))}"
            r = requests.get(url, timeout=7, headers=headers)
            if r.status_code == 200:
                data = r.json()
                extract = data.get("extract", "")
                if extract and len(extract) > 40:
                    return {"lang": lang, "title": data.get("title", query), "extract": extract[:500]}
        except:
            continue
    return {}

def search_google(query: str, api_key: str, cx: str, num: int = 2) -> list:
    if not api_key or not cx:
        return []
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": api_key, "cx": cx, "q": query, "num": num}
        r = requests.get(url, params=params, timeout=8)
        if r.status_code == 200:
            return [{"title": it.get("title",""), "snippet": it.get("snippet",""), "link": it.get("link","")}
                    for it in r.json().get("items", [])]
    except:
        pass
    return []

def call_gemini(prompt: str, api_key: str) -> str:
    if not api_key:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for model in ["gemini-2.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash"]:
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                text = resp.text.strip()
                if text and len(text) > 15:
                    return text[:600]
            except:
                continue
    except:
        pass
    return ""

def read_local_files(folder=KNOWLEDGE_FOLDER) -> list:
    results = []
    if not os.path.exists(folder):
        return results
    for fname in os.listdir(folder):
        if fname.endswith(".txt"):
            try:
                with open(os.path.join(folder, fname), "r", encoding="utf-8") as f:
                    results.append({"file": fname, "content": f.read()[:800]})
            except:
                pass
    return results

# ==================== 4. CURIOSITY ENGINE ====================
class UpgradedCuriosityEngine:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.last_action_time = 0

    def get_candidates(self):
        skip = ["Thông tin bên ngoài", "Phân tích AI", "Nội dung file"]
        return [n for n, info in self.memory.nodes.items() if info.get("type") not in skip]

    def should_act(self) -> bool:
        return time.time() - self.last_action_time >= 12 and len(self.get_candidates()) > 0

    def evaluate(self, text: str) -> float:
        if not text or len(text) < 30:
            return 0.2
        s = 0.5
        if len(text) > 100: s += 0.2
        if any(k in text.lower() for k in ["là", "được", "có", "sử dụng"]): s += 0.2
        return min(1.0, s)

    def explore(self, entity_id: str) -> dict:
        self.last_action_time = time.time()
        results = []

        # Wikipedia
        wiki = search_wikipedia(entity_id)
        if wiki:
            sc = self.evaluate(wiki["extract"])
            node = f"wiki_{int(time.time())%100000}"
            self.memory.add_entity(node, "Thông tin bên ngoài", {
                "source": f"wiki-{wiki['lang']}", "content": wiki["extract"],
                "about": entity_id, "usefulness": round(sc,2)
            })
            self.memory.add_relation(entity_id, node, "từ wikipedia", weight=round(2+sc,1))
            results.append({"source": f"Wiki-{wiki['lang']}", "score": sc, "preview": wiki["extract"][:90]})

        # Google
        if GOOGLE_API_KEY and GOOGLE_CX:
            for i, g in enumerate(search_google(entity_id, GOOGLE_API_KEY, GOOGLE_CX)):
                snip = g.get("snippet","")
                if len(snip) > 25:
                    sc = self.evaluate(snip)
                    node = f"gg_{int(time.time())%100000}_{i}"
                    self.memory.add_entity(node, "Thông tin bên ngoài", {
                        "source": "google", "content": f"{g.get('title','')}: {snip}",
                        "about": entity_id, "url": g.get("link",""), "usefulness": round(sc,2)
                    })
                    self.memory.add_relation(entity_id, node, "từ google", weight=round(1.8+sc,1))
                    results.append({"source": "Google", "score": sc, "preview": snip[:80]})

        # Gemini
        best = max([r["score"] for r in results], default=0)
        if GEMINI_API_KEY and best < 0.7:
            ai = call_gemini(f"Giải thích ngắn gọn bằng tiếng Việt về '{entity_id}'.", GEMINI_API_KEY)
            if ai:
                sc = self.evaluate(ai)
                node = f"ai_{int(time.time())%100000}"
                self.memory.add_entity(node, "Phân tích AI", {
                    "source": "gemini", "content": ai, "about": entity_id, "usefulness": round(sc,2)
                })
                self.memory.add_relation(entity_id, node, "phân tích AI", weight=round(2+sc,1))
                results.append({"source": "Gemini", "score": sc, "preview": ai[:90]})

        # File local
        for lf in read_local_files():
            if entity_id.lower() in lf["content"].lower():
                node = f"file_{int(time.time())%100000}"
                self.memory.add_entity(node, "Nội dung file", {
                    "source": lf["file"], "content": lf["content"][:400], "about": entity_id
                })
                self.memory.add_relation(entity_id, node, "trong file", weight=2.1)
                results.append({"source": f"File:{lf['file']}", "score": 0.6, "preview": lf["content"][:70]})
                break

        self.memory.save_to_file()
        if results:
            best = max(results, key=lambda x: x["score"])
            return {"success": True, "target": entity_id,
                    "detail": f"{len(results)} nguồn | Tốt nhất: {best['source']} ({best['score']:.2f})",
                    "results": results}
        return {"success": False, "detail": "Không thu thập được"}

    def auto_once(self) -> dict:
        if not self.should_act():
            return {"success": False}
        cands = self.get_candidates()
        if not cands:
            return {"success": False}
        return self.explore(random.choice(cands))

# ==================== 5. KHỞI TẠO ====================
if "memory" not in st.session_state:
    st.session_state.memory = AGIKnowledgeMemory()
if "running" not in st.session_state:
    st.session_state.running = False
if "curiosity" not in st.session_state:
    st.session_state.curiosity = UpgradedCuriosityEngine(st.session_state.memory)
if "log" not in st.session_state:
    st.session_state.log = []

memory = st.session_state.memory
extractor = AGIKnowledgeExtractor(memory)
curiosity = st.session_state.curiosity

# ==================== 6. GIAO DIỆN ====================
st.title("🧠 AGI Cognitive Dashboard")
st.caption("Wikipedia + Google + Gemini + Upload file")

st.sidebar.header("Điều khiển")
if st.sidebar.button("🛑 Dừng" if st.session_state.running else "🟢 Bật chạy ngầm", use_container_width=True):
    st.session_state.running = not st.session_state.running
    st.rerun()

if st.session_state.log:
    st.sidebar.divider()
    st.sidebar.markdown("**Nhật ký**")
    for l in reversed(st.session_state.log[-5:]):
        st.sidebar.caption(f"• {l}")

tab1, tab2, tab3 = st.tabs(["📥 Nhập liệu & Upload", "📊 Thông tin", "🌐 Khám phá"])

with tab1:
    st.subheader("Nạp văn bản")
    raw = st.text_area("Văn bản:", "Mèo là động vật nuôi.\nAGI là trí tuệ nhân tạo.", height=80)
    if st.button("Trích xuất văn bản", use_container_width=True):
        n = extractor.extract_and_ingest(raw)
        st.success(f"Đã nạp {n}")
        st.rerun()

    st.divider()
    st.subheader("Upload file .txt")
    uploaded = st.file_uploader("Chọn file kiến thức (.txt)", type=["txt"], accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            path = os.path.join(KNOWLEDGE_FOLDER, f.name)
            with open(path, "wb") as out:
                out.write(f.getbuffer())
            st.success(f"Đã lưu: {f.name}")
        st.rerun()

    # Liệt kê file đã có
    files = [f for f in os.listdir(KNOWLEDGE_FOLDER) if f.endswith(".txt")]
    if files:
        st.caption(f"File trong thư mục: {', '.join(files)}")

with tab2:
    c1, c2 = st.columns(2)
    c1.metric("Nodes", len(memory.nodes))
    c2.metric("Edges", len(memory.edges))
    infos = [(n, i) for n, i in memory.nodes.items()
             if i.get("type") in ["Thông tin bên ngoài", "Phân tích AI", "Nội dung file"]]
    if infos:
        st.subheader("Thông tin đã thu thập")
        for nid, info in reversed(infos[-12:]):
            p = info.get("properties", {})
            label = f"[{p.get('source','')}] {p.get('about','?')}"
            if p.get("usefulness"):
                label += f" ({p['usefulness']})"
            with st.expander(label):
                st.write(p.get("content", ""))
                if p.get("url"):
                    st.caption(p["url"])
    else:
        st.info("Chưa có thông tin bên ngoài.")

with tab3:
    cands = curiosity.get_candidates()
    if cands:
        sel = st.selectbox("Chọn thực thể:", cands)
        if st.button("🔍 Khám phá đa nguồn", use_container_width=True):
            with st.spinner("Đang tìm Wikipedia, Google, Gemini, file..."):
                res = curiosity.explore(sel)
            if res.get("success"):
                st.success(res["detail"])
                for r in res.get("results", []):
                    st.caption(f"• **{r['source']}** ({r['score']:.2f}): {r['preview']}")
                st.session_state.log.append(f"{sel} → {res['detail']}")
                st.rerun()
            else:
                st.warning(res.get("detail"))
    else:
        st.info("Hãy nạp văn bản hoặc upload file trước.")

# ==================== 7. BACKGROUND ====================
if st.session_state.running:
    res = curiosity.auto_once()
    if res.get("success"):
        st.toast(f"🌐 {res['target']} → {res['detail']}")
        st.session_state.log.append(f"{res['target']} → {res['detail']}")
    time.sleep(12)
    st.rerun()
