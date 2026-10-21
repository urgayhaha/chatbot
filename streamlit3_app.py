import streamlit as st
import json
import os
import time
import re
import pandas as pd
import random
import requests
from datetime import datetime
from google import genai

st.set_page_config(page_title="AGI Cognitive Dashboard", page_icon="🧠", layout="wide")

# ==================== 1. BỘ NHỚ DÀI HẠN ====================
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
        data = {
            "nodes": self.nodes, "edges": self.edges,
            "meta": {"total_nodes": len(self.nodes), "total_edges": len(self.edges), "saved_at": time.time()}
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", [])

# ==================== 2. TRÍCH XUẤT TRI THỨC ====================
class AGIKnowledgeExtractor:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.relation_patterns = [
            (r"(.+?)\s+(là|bao gồm|được phân loại là|thuộc về)\s+(.+)", "là / thuộc về"),
            (r"(.+?)\s+(sử dụng|áp dụng|dùng|vận hành bằng)\s+(.+)", "sử dụng"),
            (r"(.+?)\s+(phát triển|tạo ra|nghiên cứu|mô phỏng)\s+(.+)", "tạo ra / mô phỏng"),
            (r"(.+?)\s+(yêu cầu|cần có|phụ thuộc vào)\s+(.+)", "yêu cầu"),
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
            if not matched:
                clean_concept = sentence.strip()
                if len(clean_concept) >= 2:
                    self.memory.add_entity(clean_concept, "Khái niệm thô")
                    count += 1
        self.memory.save_to_file()
        return count

# ==================== 3. WORLD MODEL TÍCH HỢP GEMINI AI ====================
class AGIWorldModel:
    def __init__(self, memory_system):
        self.memory = memory_system

    def simulate_with_ai(self, node_id: str, api_key: str) -> dict:
        if not api_key:
            return {
                "domain": "Fallback Rule",
                "detected_action": "manual_input_required",
                "action_description": "Chưa nhập Gemini API Key",
                "predicted_outcome": "Vui lòng nhập API Key ở sidebar để AI phân tích thực tế.",
                "estimated_risk": 0.0,
                "simulated_success": False
            }
        
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Bạn là World Model (Mô hình thế giới vật lý và nhận thức) của hệ thống AGI.
            Hãy phân tích tình huống/thực thể sau đây: "{node_id}"
            
            Hãy đóng vai trò là một mô hình động lực học và nhân quả nâng cao, trả về kết quả phân tích theo đúng cấu trúc JSON gồm 5 trường sau (không kèm markdown thừa):
            {{
              "domain": "Physics & Dynamics hoặc Cognitive Science",
              "detected_action": "tên hành động cốt lõi bằng tiếng Anh",
              "action_description": "mô tả ngắn gọn hành động bằng tiếng Việt",
              "predicted_outcome": "dự đoán chi tiết hệ quả vật lý, vận tốc, quỹ đạo hoặc quy luật nhân quả của tình huống trên bằng tiếng Việt",
              "estimated_risk": số thực từ 0.0 đến 1.0 đánh giá mức độ nguy hiểm hoặc rủi ro
            }}
            """
            
            # Sử dụng tên model gemini-2.5-flash chuẩn
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            
            clean_text = response.text.strip()
            clean_text = re.sub(r"^```json\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)
            
            data = json.loads(clean_text)
            data["target"] = node_id
            data["simulated_success"] = True
            return data
            
        except Exception as e:
            return {
                "target": node_id,
                "domain": "AI Error",
                "detected_action": "error",
                "action_description": "Lỗi kết nối hoặc xử lý từ Gemini API",
                "predicted_outcome": f"Chi tiết lỗi: {str(e)}",
                "estimated_risk": 1.0,
                "simulated_success": False
            }
# ==================== 4. ĐỘNG CƠ TÒ MÒ ====================
class AdvancedCuriosityEngine:
    def __init__(self, memory_system, world_model: AGIWorldModel):
        self.memory = memory_system
        self.world_model = world_model
        self.active_goals = []

    def scan_and_rank(self, top_k=50):
        results = []
        for node_id in self.memory.nodes:
            results.append({
                "entity": node_id,
                "score": 5.0,
                "type": self.memory.nodes[node_id].get("type", "Unknown")
            })
        return results[:top_k]

    def update_long_term_goals(self):
        ranked = self.scan_and_rank(top_k=5)
        self.active_goals = [r["entity"] for r in ranked]

    def auto_explore_once(self) -> dict:
        self.update_long_term_goals()
        if not self.active_goals:
            return {"success": False, "reason": "Không có mục tiêu"}
        target = self.active_goals[0]
        return {"success": True, "target": target, "action": "ai_world_model_active"}

# ==================== 5. KHỞI TẠO TRẠNG THÁI ====================
if "agi_memory" not in st.session_state:
    st.session_state.agi_memory = AGIKnowledgeMemory()
if "background_running" not in st.session_state:
    st.session_state.background_running = False

if "world_model_ai_v3" not in st.session_state:
    st.session_state.world_model_ai_v3 = AGIWorldModel(st.session_state.agi_memory)

if "curiosity_engine_ai_v3" not in st.session_state:
    st.session_state.curiosity_engine_ai_v3 = AdvancedCuriosityEngine(st.session_state.agi_memory, st.session_state.world_model_ai_v3)

if "explore_log" not in st.session_state:
    st.session_state.explore_log = []

memory = st.session_state.agi_memory
extractor = AGIKnowledgeExtractor(memory)
world_model = st.session_state.world_model_ai_v3
curiosity = st.session_state.curiosity_engine_ai_v3

# ==================== 6. GIAO DIỆN DASHBOARD ====================
st.title("🧠 AGI Cognitive Core Dashboard")
st.caption("Kiến trúc đỉnh cao: Động lực nội tại + World Model tích hợp Gemini AI Phân tích Động lực học")

st.sidebar.header("⚙️ Cấu hình AI & Hệ thống")
gemini_api_key = st.sidebar.text_input("🔑 Nhập Gemini API Key:", type="password", help="Nhập khóa API để AI phân tích World Model trực tiếp.")

if st.sidebar.button("🛑 Dừng chạy ngầm" if st.session_state.background_running else "🟢 Bật chạy ngầm", use_container_width=True):
    st.session_state.background_running = not st.session_state.background_running
    st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["📥 Nhập liệu & File", "📊 Đồ thị Tri thức", "🌍 AI World Model Phân tích", "🤖 Trợ lý LLM"])

with tab1:
    st.subheader("Nạp văn bản hoặc Tệp tin Local")
    raw = st.text_area("Nhập sự việc/thực thể cần phân tích:", "Con mèo đang băng qua đường nhưng nhiều xe cộ đang di chuyển rất nhanh.", height=100)
    if st.button("🚀 Trích xuất vào Đồ thị", use_container_width=True):
        n = extractor.extract_and_ingest(raw)
        st.success(f"Đã nạp {n} thực thể vào bộ nhớ tri thức!")
        st.rerun()

with tab2:
    st.subheader("Bảng Đồ thị Tri thức")
    c1, c2 = st.columns(2)
    c1.metric("Tổng Thực thể (Nodes)", len(memory.nodes))
    c2.metric("Tổng Mối quan hệ (Edges)", len(memory.edges))
    
    ranked_nodes = curiosity.scan_and_rank(top_k=50)
    if ranked_nodes:
        df_nodes = pd.DataFrame([{
            "Thực thể": item["entity"].upper(),
            "Phân loại": item["type"],
        } for item in ranked_nodes])
        st.dataframe(df_nodes, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("🌍 AI World Model: Phân tích Sự kiện Thời gian thực")
    st.info("Hệ thống sẽ gọi trực tiếp Gemini AI để mô phỏng vật lý, tốc độ phản ứng và dự đoán quỹ đạo sự kiện.")
    
    node_keys = list(memory.nodes.keys())
    if node_keys:
        selected_node = st.selectbox("Chọn thực thể để Gemini AI phân tích:", node_keys)
        
        if st.button("🔮 Yêu cầu Gemini AI Mô Phỏng Thế Giới", use_container_width=True):
            if not gemini_api_key:
                st.error("⚠️ Vui lòng nhập Gemini API Key ở thanh sidebar bên trái trước khi chạy phân tích AI!")
            else:
                with st.spinner("🤖 Gemini AI đang mô phỏng không gian và động lực học vật lý..."):
                    pred = world_model.simulate_with_ai(selected_node, gemini_api_key)
                
                st.markdown("### 📝 Kết quả Phân tích từ Gemini AI World Model:")
                st.markdown(f"- **Thực thể phân tích:** `{pred.get('target', '').upper()}`")
                st.markdown(f"- **Lĩnh vực nhận diện:** `{pred.get('domain')}`")
                st.markdown(f"- **Hành động cốt lõi:** `{pred.get('detected_action')}` *({pred.get('action_description')})*")
                st.markdown(f"- **Hệ quả dự kiến & Quỹ đạo mô phỏng:** **{pred.get('predicted_outcome')}**")
                st.markdown(f"- **Chỉ số rủi ro ước tính:** `{pred.get('estimated_risk')}`")
                
                if pred.get('simulated_success'):
                    st.success("✅ **AI mô phỏng thành công:** Hệ thống đã hiểu rõ quy luật nhân quả của sự việc!")
                else:
                    st.error(f"❌ **Phân tích gặp sự cố:** {pred.get('predicted_outcome')}")
    else:
        st.warning("Chưa có thực thể trong bộ nhớ. Hãy sang tab 'Nhập liệu' để thêm sự việc (VD: con mèo đang băng qua đường...).")

with tab4:
    st.subheader("Trợ lý LLM / Hỏi đáp tri thức AGI")
    user_query = st.text_input("Đặt câu hỏi cho AGI:")
    if user_query:
        query_lower = user_query.lower()
        matched_nodes = [n for n in memory.nodes if query_lower in n]
        if matched_nodes:
            for node in matched_nodes:
                st.markdown(f"- Phát hiện thực thể: `{node.upper()}` trong bộ nhớ trí tuệ.")
        else:
            st.warning("Không tìm thấy trong bộ nhớ dài hạn.")

# ==================== 7. VÒNG LẶP NGẦM ====================
if st.session_state.background_running:
    result = curiosity.auto_explore_once()
    if result.get("success"):
        st.toast(f"🌍 Vòng lặp ngầm đang quét mục tiêu: {result.get('target').upper()}")
    time.sleep(5)
    st.rerun()
