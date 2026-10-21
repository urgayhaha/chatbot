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
    """Tìm kiếm Wikipedia (miễn phí)"""
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        r = requests.get(url, timeout=6, headers={"User-Agent": "AGI-Dashboard/1.0"})
        if r.status_code == 200:
            data = r.json()
            extract = data.get("extract", "")
            return extract[:400] if extract else "Không có tóm tắt"
        return "Không tìm thấy trên Wikipedia"
    except Exception as e:
        return f"Lỗi Wikipedia: {str(e)}"

def call_gemini(prompt: str, api_key: str) -> str:
    """Gọi Gemini API"""
    if not api_key:
        return "Chưa có API Key"
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text.strip()[:500]
    except Exception as e:
        return f"Lỗi Gemini: {str(e)}"

# ==================== 4. CURIOSITY + EXTERNAL TOOLS ====================
class ExternalCuriosityEngine:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.exploration_history = []
        self.last_action_time = 0

    def get_candidates(self):
        """Lấy các node thật (không phải node hệ thống tạo)"""
        skip_types = ["Giả thuyết", "Câu hỏi khám phá", "Thông tin bên ngoài", "Phân tích AI"]
        return [n for n, info in self.memory.nodes.items()
                if info.get("type") not in skip_types]

    def should_act(self) -> bool:
        if time.time() - self.last_action_time < 10:
            return False
        return len(self.get_candidates()) > 0

    def external_explore(self, entity_id: str, api_key: str = "") -> dict:
        """Khám phá bên ngoài: Wikipedia hoặc Gemini"""
        self.last_action_time = time.time()
        action = random.choice(["wikipedia", "gemini"] if api_key else ["wikipedia"])

        if action == "wikipedia":
            info = search_wikipedia(entity_id)
            if "Không tìm thấy" not in info and "Lỗi" not in info:
                node_name = f"wiki_{int(time.time()) % 100000}"
                self.memory.add_entity(node_name, "Thông tin bên ngoài", {"source": "wikipedia", "content": info})
                self.memory.add_relation(entity_id, node_name, "có thông tin từ wikipedia", weight=2.5)
                self.memory.save_to_file()
                return {"success": True, "action": "wikipedia", "target": entity_id, "detail": info[:100]}
            return {"success": False, "action": "wikipedia", "detail": info}

        else:  # gemini
            prompt = f"Giải thích ngắn gọn (2-3 câu) về khái niệm hoặc thực thể: '{entity_id}'. Trả lời bằng tiếng Việt."
            answer = call_gemini(prompt, api_key)
            if "Lỗi" not in answer and "Chưa có" not in answer:
                node_name = f"ai_{int(time.time()) % 100000}"
                self.memory.add_entity(node_name, "Phân tích AI", {"source": "gemini", "content": answer})
                self.memory.add_relation(entity_id, node_name, "được phân tích bởi AI", weight=2.5)
                self.memory.save_to_file()
                return {"success": True, "action": "gemini", "target": entity_id, "detail": answer[:100]}
            return {"success": False, "action": "gemini", "detail": answer}

    def auto_explore_once(self, api_key: str = "") -> dict:
        if not self.should_act():
            return {"success": False, "reason": "Đang nghỉ"}
        candidates = self.get_candidates()
        if not candidates:
            return {"success": False, "reason": "Không có mục tiêu"}
        # Ưu tiên node chưa có thông tin bên ngoài
        target = random.choice(candidates)
        result = self.external_explore(target, api_key)
        if result.get("success"):
            self.exploration_history.append({"target": target, "action": result["action"], "time": time.time()})
        return result

# ==================== 5. KHỞI TẠO ====================
if "agi_memory" not in st.session_state:
    st.session_state.agi_memory = AGIKnowledgeMemory()
if "background_running" not in st.session_state:
    st.session_state.background_running = False
if "curiosity" not in st.session_state:
    st.session_state.curiosity = ExternalCuriosityEngine(st.session_state.agi_memory)
if "explore_log" not in st.session_state:
    st.session_state.explore_log = []

memory = st.session_state.agi_memory
extractor = AGIKnowledgeExtractor(memory)
curiosity = st.session_state.curiosity

# ==================== 6. GIAO DIỆN ====================
st.title("🧠 AGI Cognitive Dashboard")
st.caption("Kết nối bên ngoài: Wikipedia + Gemini tự động")

st.sidebar.header("⚙️ Cấu hình")
gemini_key = st.sidebar.text_input("Gemini API Key (tùy chọn):", type="password")
if st.sidebar.button("🛑 Dừng" if st.session_state.background_running else "🟢 Bật chạy ngầm", use_container_width=True):
    st.session_state.background_running = not st.session_state.background_running
    st.rerun()

if st.session_state.explore_log:
    st.sidebar.divider()
    st.sidebar.markdown("### Nhật ký")
    for log in reversed(st.session_state.explore_log[-5:]):
        st.sidebar.caption(f"• {log}")

tab1, tab2, tab3 = st.tabs(["📥 Nhập liệu", "📊 Đồ thị", "🌐 Khám phá bên ngoài"])

with tab1:
    st.subheader("Nạp văn bản")
    raw = st.text_area("Văn bản:", "AGI sử dụng mạng neural.\nKitsune là sinh vật huyền thoại.", height=100)
    if st.button("🚀 Trích xuất", use_container_width=True):
        n = extractor.extract_and_ingest(raw)
        st.success(f"Đã nạp {n} thực thể")
        st.rerun()

with tab2:
    c1, c2 = st.columns(2)
    c1.metric("Nodes", len(memory.nodes))
    c2.metric("Edges", len(memory.edges))
    if memory.edges:
        df = pd.DataFrame([{"Từ": e["source"], "Quan hệ": e["relation"], "Đến": e["target"], "W": e["weight"]} for e in memory.edges])
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Khám phá bên ngoài")
    candidates = curiosity.get_candidates()
    if candidates:
        selected = st.selectbox("Chọn thực thể:", candidates)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📖 Tìm Wikipedia", use_container_width=True):
                res = curiosity.external_explore(selected, "")
                if res.get("success"):
                    st.success(res.get("detail"))
                    st.session_state.explore_log.append(f"Wiki: {selected}")
                    st.rerun()
                else:
                    st.warning(res.get("detail"))
        with c2:
            if st.button("🤖 Hỏi Gemini", use_container_width=True):
                if not gemini_key:
                    st.error("Cần nhập API Key")
                else:
                    res = curiosity.external_explore(selected, gemini_key)
                    if res.get("success"):
                        st.success(res.get("detail"))
                        st.session_state.explore_log.append(f"Gemini: {selected}")
                        st.rerun()
                    else:
                        st.warning(res.get("detail"))
    else:
        st.info("Chưa có thực thể. Hãy nạp văn bản trước.")

# ==================== 7. BACKGROUND (tự động gọi công cụ) ====================
if st.session_state.background_running:
    result = curiosity.auto_explore_once(gemini_key)
    if result.get("success"):
        msg = f"{result['action'].upper()}: {result['target']} → {result.get('detail','')[:60]}"
        st.toast(f"🌐 {msg}")
        st.session_state.explore_log.append(msg)
    time.sleep(8)
    st.rerun()
