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

# ==================== 3. WORLD MODEL TỰ ĐỘNG NHẬN DIỆN & DỰ ĐOÁN ====================
class AGIWorldModel:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.causal_rules = {
            "fetch_internet": {"description": "Cào tri thức từ Internet", "predicted_outcome": "Giảm độ bất định, mở rộng dữ liệu thực tế", "success_prob": 0.85},
            "internal_goal_link": {"description": "Liên kết mục tiêu nội bộ", "predicted_outcome": "Củng cố cấu trúc đồ thị nhận thức", "success_prob": 0.75},
            "create_hypothesis": {"description": "Tạo giả thuyết nhận thức", "predicted_outcome": "Mở rộng không gian suy luận giả định", "success_prob": 0.60}
        }

    def auto_decide_action(self, node_id: str) -> str:
        degree = sum(1 for e in self.memory.edges if e["source"] == node_id or e["target"] == node_id)
        node_info = self.memory.nodes.get(node_id, {})
        node_type = node_info.get("type", "")

        if degree <= 1 or node_type == "Khái niệm thô":
            return "fetch_internet"
        elif degree <= 3:
            return "internal_goal_link"
        else:
            return "create_hypothesis"

    def simulate_and_predict(self, node_id: str) -> dict:
        chosen_action = self.auto_decide_action(node_id)
        rule = self.causal_rules[chosen_action]

        degree = sum(1 for e in self.memory.edges if e["source"] == node_id or e["target"] == node_id)
        risk_score = round(max(0.05, 1.0 - (degree * 0.25)), 2)
        simulated_success = random.random() < (rule["success_prob"] * (1.0 - risk_score * 0.2))

        return {
            "target": node_id,
            "detected_action": chosen_action,
            "action_description": rule["description"],
            "predicted_outcome": rule["predicted_outcome"],
            "estimated_risk": risk_score,
            "simulated_success": simulated_success
        }

# ==================== 4. ĐỘNG CƠ TÒ MÒ TÍCH HỢP WORLD MODEL ====================
class AdvancedCuriosityEngine:
    def __init__(self, memory_system, world_model: AGIWorldModel):
        self.memory = memory_system
        self.world_model = world_model
        self.exploration_history = []
        self.node_visit_count = {}
        self.last_exploration_time = {}
        self.active_goals = []

    def compute_curiosity_score(self, node_id: str) -> dict:
        if node_id not in self.memory.nodes:
            return {"total": 0.0}
        node = self.memory.nodes[node_id]
        node_type = node.get("type", "")
        
        if node_type in ["Giả thuyết", "Câu hỏi khám phá", "Kiến thức ngoài"]:
            return {"total": 0.1}

        scores = {}
        degree = sum(1 for e in self.memory.edges if e["source"] == node_id or e["target"] == node_id)
        scores["isolation"] = max(0.0, 3.0 - degree * 0.8)

        age_hours = (time.time() - node.get("created_at", time.time())) / 3600
        scores["recency"] = max(0.0, 2.0 * (1.0 - min(age_hours / 24, 1.0)))

        times_explored = self.node_visit_count.get(node_id, 0)
        scores["novelty"] = max(0.0, 2.5 - times_explored * 1.0)

        last_time = self.last_exploration_time.get(node_id, 0)
        hours_since = (time.time() - last_time) / 3600 if last_time > 0 else 24
        scores["staleness"] = min(2.0, hours_since / 6)

        scores["type_bonus"] = 1.5 if node_type in ["Khái niệm thô", "Unknown", ""] else 0.2

        weak_links = sum(1 for e in self.memory.edges
                         if (e["source"] == node_id or e["target"] == node_id) and e["weight"] < 2.0)
        scores["weak_links"] = min(1.5, weak_links * 0.5)

        raw_total = sum(scores.values())
        if node_id in self.last_exploration_time and time.time() - self.last_exploration_time[node_id] < 60:
            raw_total *= 0.1

        scores["total"] = round(min(10.0, max(0.0, raw_total / 1.25)), 2)
        return scores

    def scan_and_rank(self, top_k=50):
        results = []
        for node_id in self.memory.nodes:
            detail = self.compute_curiosity_score(node_id)
            total = detail.get("total", 0)
            results.append({
                "entity": node_id,
                "score": total,
                "type": self.memory.nodes[node_id].get("type", "Unknown")
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def update_long_term_goals(self):
        ranked = self.scan_and_rank(top_k=5)
        self.active_goals = [r["entity"] for r in ranked if r["score"] > 2.0]

    def fetch_wikipedia_knowledge(self, query: str) -> dict:
        try:
            url = f"https://vi.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json"
            headers = {"User-Agent": "AGICognitiveBot/1.0"}
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()
            search_results = data.get("query", {}).get("search", [])
            
            if search_results:
                title = search_results[0]["title"]
                snippet = re.sub(r'<.*?>', '', search_results[0]["snippet"])
                
                if query in self.memory.nodes:
                    self.memory.nodes[query]["type"] = "Tri thức đã kiểm chứng"

                external_node = f"wiki_{title.lower().replace(' ', '_')}"
                self.memory.add_entity(external_node, "Kiến thức ngoài", {"source": "Wikipedia", "snippet": snippet})
                self.memory.add_relation(query, external_node, "kiến thức thực tế", weight=4.5)
                
                return {"success": True, "action": "fetch_internet", "detail": f"Cào Wikipedia '{title}': {snippet[:70]}..."}
        except Exception:
            pass
        return {"success": False, "action": "fetch_internet", "detail": "Lỗi kết nối internet."}

    def auto_explore_once(self) -> dict:
        self.update_long_term_goals()
        if not self.active_goals:
            return {"success": False, "reason": "Không có mục tiêu dài hạn"}
        
        target = self.active_goals[0]
        prediction = self.world_model.simulate_and_predict(target)
        
        self.node_visit_count[target] = self.node_visit_count.get(target, 0) + 1
        self.last_exploration_time[target] = time.time()

        if prediction["simulated_success"]:
            action_type = prediction["detected_action"]
            if action_type == "fetch_internet":
                res = self.fetch_wikipedia_knowledge(target)
            elif action_type == "internal_goal_link":
                candidates = [n for n in self.memory.nodes if n != target]
                if candidates:
                    related = random.choice(candidates)
                    self.memory.add_relation(target, related, "liên kết nhận thức", weight=2.5)
                    res = {"success": True, "action": "internal_goal_link", "detail": f"Liên kết nhân quả nội bộ với {related}"}
                else:
                    res = self.fetch_wikipedia_knowledge(target)
            else:
                hypo = f"gia_thuyet_{int(time.time()) % 10000}"
                self.memory.add_entity(hypo, "Giả thuyết")
                self.memory.add_relation(target, hypo, "cần kiểm chứng", weight=2.0)
                res = {"success": True, "action": "create_hypothesis", "detail": f"Tự sinh giả thuyết {hypo}"}
        else:
            res = {"success": True, "action": "world_model_skip", "detail": f"World Model dự đoán rủi ro cao ({prediction['estimated_risk']}), tạm hoãn hành động."}

        self.exploration_history.append({"target": target, "prediction": prediction, "timestamp": time.time()})
        self.memory.save_to_file()
        
        current_score = self.compute_curiosity_score(target)["total"]
        res["target"] = target
        res["curiosity_score"] = current_score
        res["prediction_info"] = prediction
        return res

# ==================== 5. KHỞI TẠO TRẠNG THÁI AN TOÀN ====================
if "agi_memory" not in st.session_state:
    st.session_state.agi_memory = AGIKnowledgeMemory()
if "background_running" not in st.session_state:
    st.session_state.background_running = False

# Sử dụng khóa mới v2 cho world model và v4 cho curiosity engine để tránh xung đột cache
if "world_model_v2" not in st.session_state:
    st.session_state.world_model_v2 = AGIWorldModel(st.session_state.agi_memory)

if "curiosity_engine_v4" not in st.session_state:
    st.session_state.curiosity_engine_v4 = AdvancedCuriosityEngine(st.session_state.agi_memory, st.session_state.world_model_v2)

if "explore_log" not in st.session_state:
    st.session_state.explore_log = []

memory = st.session_state.agi_memory
extractor = AGIKnowledgeExtractor(memory)
world_model = st.session_state.world_model_v2
curiosity = st.session_state.curiosity_engine_v4

# ==================== 6. GIAO DIỆN DASHBOARD ====================
st.title("🧠 AGI Cognitive Core Dashboard")
st.caption("Kiến trúc đỉnh cao: Động lực nội tại + World Model Tự động nhận diện & Dự đoán nhân quả")

st.sidebar.header("⚙️ Điều khiển hệ thống")
if st.session_state.background_running:
    st.sidebar.markdown("🟢 **ĐANG CHẠY NGẦM TỰ NHẬN DIỆN**")
    if st.sidebar.button("🛑 Dừng chạy ngầm", use_container_width=True):
        st.session_state.background_running = False
        st.rerun()
else:
    st.sidebar.markdown("🔴 **ĐÃ DỪNG TIẾT KIỆM ĐIỆN**")
    if st.sidebar.button("🟢 Bật chạy ngầm", use_container_width=True):
        st.session_state.background_running = True
        st.rerun()

st.sidebar.divider()
st.sidebar.markdown(f"🎯 **Mục tiêu dài hạn:** `{len(curiosity.active_goals)} mục tiêu`")
if curiosity.active_goals:
    for g in curiosity.active_goals[:3]:
        st.sidebar.caption(f"• 📌 {g.upper()}")

st.sidebar.divider()
if st.session_state.explore_log:
    st.sidebar.markdown("### Nhật ký World Model")
    for log in reversed(st.session_state.explore_log[-5:]):
        st.sidebar.caption(f"• {log}")

tab1, tab2, tab3, tab4 = st.tabs(["📥 Nhập liệu & File", "📊 Đồ thị Tri thức", "🌍 World Model Tự Động", "🤖 Trợ lý LLM"])

with tab1:
    st.subheader("Nạp văn bản hoặc Tệp tin Local")
    uploaded_file = st.file_uploader("Tải lên file dữ liệu (.txt, .md):", type=["txt", "md", "json"])
    if uploaded_file is not None:
        file_content = uploaded_file.read().decode("utf-8")
        if st.button("📂 Trích xuất nội dung File", use_container_width=True):
            n = extractor.extract_and_ingest(file_content)
            st.success(f"Đã nạp {n} liên kết!")
            st.rerun()

    st.divider()
    raw = st.text_area("Nhập văn bản thô:", "Hệ thống AGI sử dụng mô hình nhận thức.\nWorld Model giả lập nhân quả.", height=100)
    if st.button("🚀 Trích xuất", use_container_width=True):
        n = extractor.extract_and_ingest(raw)
        st.success(f"Đã nạp {n} thực thể!")
        st.rerun()

with tab2:
    st.subheader("Bảng Đồ thị Tri thức & Độ tò mò")
    c1, c2 = st.columns(2)
    c1.metric("Tổng Thực thể (Nodes)", len(memory.nodes))
    c2.metric("Tổng Mối quan hệ (Edges)", len(memory.edges))
    
    ranked_nodes = curiosity.scan_and_rank(top_k=50)
    if ranked_nodes:
        df_nodes = pd.DataFrame([{
            "Thực thể": item["entity"].upper(),
            "Phân loại": item["type"],
            "Điểm Tò Mò": f"⭐ {item['score']}/10",
        } for item in ranked_nodes])
        st.dataframe(df_nodes, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("🌍 World Model: Tự động Nhận diện & Dự đoán Hệ quả")
    st.info("Hệ thống sẽ tự động phân tích trạng thái thực thể, tự chọn hành động và diễn giải dự đoán bằng ngôn ngữ tự nhiên.")
    
    node_keys = list(memory.nodes.keys())
    if node_keys:
        selected_node = st.selectbox("Chọn thực thể để AGI tự nhận diện & dự đoán:", node_keys)
        
        if st.button("🔮 AGI Tự Nhận Diện & Dự Đoán Hành Động", use_container_width=True):
            pred = world_model.simulate_and_predict(selected_node)
            
            st.markdown("### 📝 Kết quả Phân tích & Dự đoán từ World Model:")
            st.markdown(f"- **Thực thể phân tích:** `{pred['target'].upper()}`")
            st.markdown(f"- **Hành động hệ thống tự nhận diện:** `{pred['detected_action']}` *({pred['action_description']})*")
            st.markdown(f"- **Hệ quả dự kiến:** {pred['predicted_outcome']}")
            st.markdown(f"- **Chỉ số rủi ro ước tính:** `{pred['estimated_risk']}`")
            
            if pred['simulated_success']:
                st.success(f"✅ **Dự đoán:** Hành động khả thi và an toàn để thực thi!")
            else:
                st.warning(f"⚠️ **Dự đoán:** Rủi ro cao, hệ thống sẽ tự động hoãn hành động này.")
    else:
        st.warning("Chưa có thực thể trong bộ nhớ để phân tích.")

with tab4:
    st.subheader("Trợ lý LLM / Hỏi đáp tri thức AGI")
    user_query = st.text_input("Đặt câu hỏi cho AGI:")
    if user_query:
        query_lower = user_query.lower()
        matched_edges = [e for e in memory.edges if query_lower in e["source"] or query_lower in e["target"]]
        if matched_edges:
            for edge in matched_edges:
                st.markdown(f"- `{edge['source'].upper()}` **{edge['relation']}** `{edge['target'].upper()}`")
        else:
            st.warning("Không tìm thấy trong bộ nhớ dài hạn.")

# ==================== 7. VÒNG LẶP NGẦM TỰ TRỊ ====================
if st.session_state.background_running:
    result = curiosity.auto_explore_once()
    if result.get("success"):
        pred_info = result.get("prediction_info", {})
        msg = f"Tự nhận diện [{pred_info.get('detected_action')}] cho '{result.get('target').upper()}' | Rủi ro: {pred_info.get('estimated_risk')} → {result.get('detail','')}"
        st.toast(f"🌍 {msg}")
        st.session_state.explore_log.append(msg)
    time.sleep(5)
    st.rerun()
