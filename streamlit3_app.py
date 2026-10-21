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

# ==================== API KEY ====================
GEMINI_API_KEY = "AQ.Ab8RN6I52wKSVq78IGjJl_zbSKfCVEgLDIEzhC_yES-ouv99KA"

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
def search_wikipedia(query: str) -> str:
    headers = {"User-Agent": "AGI-Dashboard/1.0"}
    try:
        url_vi = f"https://vi.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query.replace(' ', '_'))}"
        r = requests.get(url_vi, timeout=8, headers=headers)
        if r.status_code == 200:
            extract = r.json().get("extract", "")
            if extract:
                return extract[:500]
        url_en = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query.replace(' ', '_'))}"
        r2 = requests.get(url_en, timeout=8, headers=headers)
        if r2.status_code == 200:
            extract = r2.json().get("extract", "")
            if extract:
                return extract[:500]
        return ""
    except:
        return ""

def call_gemini(prompt: str, api_key: str) -> str:
    if not api_key:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash"]:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                text = response.text.strip()
                if text and len(text) > 15:
                    return text[:600]
            except:
                continue
        return ""
    except:
        return ""

def read_local_files(folder="knowledge_files", max_files=5) -> list:
    results = []
    if not os.path.exists(folder):
        os.makedirs(folder)
        return results
    for fname in os.listdir(folder)[:max_files]:
        if fname.endswith(".txt"):
            try:
                with open(os.path.join(folder, fname), "r", encoding="utf-8") as f:
                    content = f.read()[:800]
                    results.append({"file": fname, "content": content})
            except:
                pass
    return results

# ==================== 4. CURIOSITY ENGINE NÂNG CẤP ====================
class UpgradedCuriosityEngine:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.last_action_time = 0
        self.action_history = []

    def get_candidates(self):
        skip = ["Thông tin bên ngoài", "Phân tích AI", "Nội dung file"]
        return [n for n, info in self.memory.nodes.items() if info.get("type") not in skip]

    def should_act(self) -> bool:
        return time.time() - self.last_action_time >= 12 and len(self.get_candidates()) > 0

    def evaluate_result(self, content: str) -> float:
        if not content or len(content) < 30:
            return 0.2
        score = 0.5
        if len(content) > 120:
            score += 0.25
        if any(kw in content.lower() for kw in ["là", "được", "có", "sử dụng", "bao gồm", "là một"]):
            score += 0.2
        return min(1.0, score)

    def explore_with_strategy(self, entity_id: str, api_key: str = "") -> dict:
        self.last_action_time = time.time()
        results = []

        # Wikipedia
        wiki = search_wikipedia(entity_id)
        wiki_score = self.evaluate_result(wiki)
        if wiki_score > 0.35:
            node = f"wiki_{int(time.time()) % 100000}"
            self.memory.add_entity(node, "Thông tin bên ngoài", {
                "source": "wikipedia", "content": wiki, "about": entity_id, "usefulness": round(wiki_score, 2)
            })
            self.memory.add_relation(entity_id, node, "có thông tin từ wikipedia", weight=round(2.0 + wiki_score, 1))
            results.append({"source": "wikipedia", "score": wiki_score, "preview": wiki[:100]})

        # Gemini nếu Wikipedia chưa đủ tốt
        if api_key and wiki_score < 0.75:
            prompt = f"Giải thích ngắn gọn, chính xác bằng tiếng Việt về: '{entity_id}'. Tập trung vào định nghĩa và đặc điểm chính. Chỉ trả lời nội dung."
            ai = call_gemini(prompt, api_key)
            ai_score = self.evaluate_result(ai)
            if ai_score > 0.35:
                node = f"ai_{int(time.time()) % 100000}"
                self.memory.add_entity(node, "Phân tích AI", {
                    "source": "gemini", "content": ai, "about": entity_id, "usefulness": round(ai_score, 2)
                })
                self.memory.add_relation(entity_id, node, "được phân tích bởi AI", weight=round(2.0 + ai_score, 1))
                results.append({"source": "gemini", "score": ai_score, "preview": ai[:100]})

        # File local
        for lf in read_local_files():
            if entity_id.lower() in lf["content"].lower() or entity_id.lower() in lf["file"].lower():
                node = f"file_{int(time.time()) % 100000}"
                self.memory.add_entity(node, "Nội dung file", {
                    "source": lf["file"], "content": lf["content"][:500], "about": entity_id
                })
                self.memory.add_relation(entity_id, node, "được đề cập trong file", weight=2.2)
                results.append({"source": f"file:{lf['file']}", "score": 0.65, "preview": lf["content"][:80]})
                break

        self.memory.save_to_file()

        if results:
            best = max(results, key=lambda x: x["score"])
            self.action_history.append({
                "target": entity_id,
                "sources": [r["source"] for r in results],
                "best": best["source"],
                "time": time.time()
            })
            return {
                "success": True,
                "target": entity_id,
                "action": "multi",
                "detail": f"{len(results)} nguồn | Tốt nhất: {best['source']} ({best['score']:.2f})",
                "results": results
            }
        return {"success": False, "detail": "Không thu thập được thông tin hữu ích"}

    def auto_explore_once(self, api_key: str = "") -> dict:
        if not self.should_act():
            return {"success": False}
        candidates = self.get_candidates()
        if not candidates:
            return {"success": False}
        target = random.choice(candidates)
        return self.explore_with_strategy(target, api_key)

# ==================== 5. KHỞI TẠO ====================
if "agi_memory" not in st.session_state:
    st.session_state.agi_memory = AGIKnowledgeMemory()
if "background_running" not in st.session_state:
    st.session_state.background_running = False
if "curiosity" not in st.session_state:
    st.session_state.curiosity = UpgradedCuriosityEngine(st.session_state.agi_memory)
if "explore_log" not in st.session_state:
    st.session_state.explore_log = []

memory = st.session_state.agi_memory
extractor = AGIKnowledgeExtractor(memory)
curiosity = st.session_state.curiosity

# ==================== 6. GIAO DIỆN ====================
st.title("🧠 AGI Cognitive Dashboard")
st.caption("Khám phá đa nguồn: Wikipedia + Gemini + File local")

st.sidebar.header("⚙️ Điều khiển")
btn = "🛑 Dừng" if st.session_state.background_running else "🟢 Bật chạy ngầm"
if st.sidebar.button(btn, use_container_width=True):
    st.session_state.background_running = not st.session_state.background_running
    st.rerun()

if st.session_state.explore_log:
    st.sidebar.divider()
    st.sidebar.markdown("### Nhật ký")
    for log in reversed(st.session_state.explore_log[-6:]):
        st.sidebar.caption(f"• {log}")

tab1, tab2, tab3 = st.tabs(["📥 Nhập liệu", "📊 Thông tin đã thu", "🌐 Khám phá"])

with tab1:
    raw = st.text_area("Văn bản:", "Mèo là động vật nuôi.\nAGI là trí tuệ nhân tạo tổng quát.", height=90)
    if st.button("🚀 Trích xuất", use_container_width=True):
        n = extractor.extract_and_ingest(raw)
        st.success(f"Đã nạp {n} thực thể")
        st.rerun()
    st.caption("Tip: Tạo thư mục `knowledge_files` và bỏ file .txt vào để hệ thống đọc.")

with tab2:
    c1, c2 = st.columns(2)
    c1.metric("Nodes", len(memory.nodes))
    c2.metric("Edges", len(memory.edges))
    info_nodes = [(nid, info) for nid, info in memory.nodes.items()
                  if info.get("type") in ["Thông tin bên ngoài", "Phân tích AI", "Nội dung file"]]
    if info_nodes:
        st.subheader("Thông tin đã thu thập")
        for nid, info in reversed(info_nodes[-10:]):
            props = info.get("properties", {})
            about = props.get("about", "?")
            content = props.get("content", "")
            source = props.get("source", info.get("type", ""))
            score = props.get("usefulness", "")
            label = f"[{source}] {about}" + (f" ({score})" if score else "")
            with st.expander(label):
                st.write(content)
    else:
        st.info("Chưa có thông tin bên ngoài.")

with tab3:
    candidates = curiosity.get_candidates()
    if candidates:
        selected = st.selectbox("Chọn thực thể:", candidates)
        if st.button("🔍 Khám phá đa nguồn", use_container_width=True):
            with st.spinner("Đang thu thập từ Wikipedia, Gemini, file..."):
                res = curiosity.explore_with_strategy(selected, GEMINI_API_KEY)
            if res.get("success"):
                st.success(res["detail"])
                for r in res.get("results", []):
                    st.caption(f"• {r['source']}: {r['preview']}")
                st.session_state.explore_log.append(f"{selected} → {res['detail']}")
                st.rerun()
            else:
                st.warning(res.get("detail", "Thất bại"))
    else:
        st.info("Hãy nạp văn bản trước.")

# ==================== 7. BACKGROUND ====================
if st.session_state.background_running:
    result = curiosity.auto_explore_once(GEMINI_API_KEY)
    if result.get("success"):
        msg = f"{result['target']} → {result['detail']}"
        st.toast(f"🌐 {msg}")
        st.session_state.explore_log.append(msg)
    time.sleep(12)
    st.rerun()
