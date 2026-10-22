import streamlit as st
import json
import os
import time
import re
import pandas as pd
from google import genai

st.set_page_config(page_title="AGI World Model Dashboard", page_icon="🧠", layout="wide")

# ==================== BỘ NHỚ TRI THỨC ====================
class AGIMemory:
    def __init__(self, path="agi_world_memory.json"):
        self.path = path
        self.nodes = {}
        self.edges = []
        self.load()

    def add_entity(self, eid, etype="Thực thể", props=None):
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
        except Exception:
            pass

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.nodes = d.get("nodes", {})
                    self.edges = d.get("edges", [])
            except Exception:
                self.nodes = {}
                self.edges = []

# ==================== TRÍCH XUẤT SỰ KIỆN VẬT LÝ ====================
class Extractor:
    def __init__(self, mem):
        self.mem = mem

    def run(self, text):
        count = 0
        for sent in [s.strip() for s in re.split(r'[.\n;]', text) if s.strip()]:
            m = re.search(r"(.+?)\s+(là|sử dụng|dùng|tạo ra|mô phỏng|băng qua|bắt được|đang)\s+(.+)", sent, re.I)
            if m and len(m.group(1).strip()) > 1 and len(m.group(3).strip()) > 1:
                self.mem.add_entity(m.group(1), "Sự kiện/Thực thể")
                self.mem.add_entity(m.group(3), "Sự kiện/Thực thể")
                self.mem.add_relation(m.group(1), m.group(3), m.group(2))
                count += 1
            elif len(sent) > 2:
                self.mem.add_entity(sent, "Tình huống vật lý")
                count += 1
        self.mem.save()
        return count

# ==================== AI WORLD MODEL ====================
class AGIWorldModel:
    def __init__(self, memory_system):
        self.memory = memory_system

    def simulate_with_ai(self, node_id: str, api_key: str) -> dict:
        if not api_key:
            return {
                "domain": "Fallback Rule",
                "detected_action": "manual_input_required",
                "action_description": "Chưa có Gemini API Key",
                "predicted_outcome": "Vui lòng nhập API Key ở thanh sidebar.",
                "estimated_risk": 0.0,
                "adaptive_reaction": "Hệ thống chờ cung cấp khóa API hợp lệ.",
                "simulated_success": False
            }
        
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Bạn là World Model (Mô hình thế giới vật lý và nhận thức nhân quả) của hệ thống AGI.
            Hãy phân tích tình huống/thực thể sau đây: "{node_id}"
            
            Trả về kết quả phân tích dưới dạng JSON chuẩn (không kèm markdown thừa) gồm đúng các trường sau:
            {{
              "domain": "Physics & Dynamics hoặc Cognitive Science",
              "detected_action": "tên hành động cốt lõi bằng tiếng Anh",
              "action_description": "mô tả ngắn gọn hành động bằng tiếng Việt",
              "predicted_outcome": "dự đoán chi tiết hệ quả vật lý, vận tốc, quỹ đạo hoặc quy luật nhân quả của tình huống trên bằng tiếng Việt",
              "estimated_risk": số thực từ 0.0 đến 1.0 đánh giá mức độ rủi ro va chạm hoặc nguy hiểm,
              "adaptive_reaction": "chính sách phản ứng liên tục và hành động thích ứng của hệ thống được suy luận trực tiếp dựa trên hệ quả dự đoán"
            }}
            """
            
            response = client.models.generate_content(
                model='gemini-3.8-flash',
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
                "adaptive_reaction": "Hệ thống ghi nhận sự cố kết nối và duy trì vận hành an toàn.",
                "simulated_success": False
            }

# ==================== KHỞI TẠO STATE ====================
if "mem" not in st.session_state:
    st.session_state.mem = AGIMemory()

if "world_model" not in st.session_state:
    st.session_state.world_model = AGIWorldModel(st.session_state.mem)

mem = st.session_state.mem
extractor = Extractor(mem)
world_model = st.session_state.world_model

# ==================== GIAO DIỆN CHÍNH ====================
st.title("🧠 AGI World Model Dashboard")
st.caption("Hệ thống Mô hình Thế giới vật lý, dự đoán nhân quả và phản ứng thích ứng liên tục.")

# Sidebar cấu hình API Key chuẩn
st.sidebar.header("⚙️ Cấu hình hệ thống")
gemini_api_key = st.sidebar.text_input("🔑 Nhập Gemini API Key (AIza...):", type="password", help="Lấy key từ https://aistudio.google.com/")

tab1, tab2, tab3 = st.tabs(["📥 Nhập liệu Sự kiện", "📊 Đồ thị Tri thức", "🌍 AI World Model & Phản ứng"])

with tab1:
    st.subheader("Nạp kịch bản / Tình huống vật lý")
    raw_text = st.text_area("Nhập tình huống mô phỏng (VD: con mèo đang băng qua đường nhưng nhiều xe cộ đang di chuyển rất nhanh):", height=100)
    if st.button("🚀 Trích xuất vào Đồ thị Tri thức", use_container_width=True):
        if raw_text and raw_text.strip():
            n = extractor.run(raw_text)
            st.success(f"Đã trích xuất và nạp thành công {n} thực thể/sự kiện vào bộ nhớ!")
            st.rerun()

with tab2:
    st.subheader("Bảng Đồ thị Tri thức (Nodes & Edges)")
    c1, c2 = st.columns(2)
    c1.metric("Tổng Thực thể (Nodes)", len(mem.nodes))
    c2.metric("Tổng Mối quan hệ (Edges)", len(mem.edges))
    
    if mem.nodes:
        df_nodes = pd.DataFrame([{
            "Thực thể": k.upper(),
            "Phân loại": v.get("type", "Unknown")
        } for k, v in mem.nodes.items()])
        st.dataframe(df_nodes, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có thực thể nào trong bộ nhớ. Hãy nạp ở tab 'Nhập liệu Sự kiện'.")

with tab3:
    st.subheader("🌍 AI World Model: Mô phỏng & Phản ứng Thích ứng")
    st.info("Hệ thống phân tích động lực học và đưa ra phản ứng liên tục dựa trực tiếp trên kết quả mô phỏng dự đoán.")
    
    node_keys = list(mem.nodes.keys())
    if node_keys:
        selected_node = st.selectbox("Chọn sự kiện / thực thể để mô phỏng thế giới:", node_keys)
        
        if st.button("🔮 Chạy Mô Phỏng Vật Lý & Nhận Phản Ứng Thích Ứng", use_container_width=True):
            if not gemini_api_key:
                st.error("⚠️ Vui lòng nhập Gemini API Key (bắt đầu bằng AIza...) ở thanh sidebar bên trái!")
            else:
                with st.spinner("🤖 Gemini AI đang mô phỏng không gian, vận tốc và tổng hợp phản ứng thích ứng..."):
                    pred = world_model.simulate_with_ai(selected_node, gemini_api_key)
                
                st.markdown("### 📝 Kết quả Phân tích & Phản ứng từ World Model:")
                
                # Gộp toàn bộ thành một đoạn văn bản liền mạch duy nhất trong một khối thông báo duy nhất
                unified_text = (
                    f"Phân tích sự kiện '{pred.get('target', '').upper()}' thuộc lĩnh vực {pred.get('domain')}, "
                    f"với hành động cốt lõi là {pred.get('detected_action')} ({pred.get('action_description')}). "
                    f"Hệ quả vật lý và quỹ đạo dự kiến: {pred.get('predicted_outcome')} "
                    f"Chỉ số rủi ro ước tính là {pred.get('estimated_risk')}. "
                    f"Phản ứng thích ứng của hệ thống: {pred.get('adaptive_reaction')}"
                )
                
                st.success(unified_text)
    else:
        st.warning("Chưa có thực thể trong bộ nhớ. Hãy sang tab 'Nhập liệu Sự kiện' để thêm tình huống mô phỏng.")
