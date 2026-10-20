import streamlit as st
import json
import os
import time
import re
import heapq
from collections import deque

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="AGI Cognitive Dashboard", page_icon="🧠", layout="wide")

# ==================== 1. CÁC LỚP CƠ SỞ AGI ====================
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

        if source not in self.nodes: self.add_entity(source, "Unknown")
        if target not in self.nodes: self.add_entity(target, "Unknown")

        for edge in self.edges:
            if edge["source"] == source and edge["target"] == target and edge["relation"] == relation:
                edge["weight"] = min(5.0, edge["weight"] + 0.5)
                return

        self.edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": weight,
            "created_at": time.time()
        })

    def save_to_file(self):
        data = {
            "nodes": self.nodes,
            "edges": self.edges,
            "meta": {"total_nodes": len(self.nodes), "total_edges": len(self.edges), "saved_at": time.time()}
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", {})


class AGIKnowledgeExtractor:
    def __init__(self, memory_system: AGIKnowledgeMemory):
        self.memory = memory_system
        self.relation_patterns = [
            (r"(.+?)\s+(là|bao gồm|được phân loại là|thuộc về)\s+(.+)", "is_a"),
            (r"(.+?)\s+(sử dụng|áp dụng|dùng|vận hành bằng)\s+(.+)", "uses"),
            (r"(.+?)\s+(phát triển|tạo ra|nghiên cứu|mô phỏng)\s+(.+)", "creates"),
            (r"(.+?)\s+(yêu cầu|cần có|phụ thuộc vào)\s+(.+)", "requires"),
            (r"(.+?)\s+(kết nối với|liên kết với|tương tác với)\s+(.+)", "connects_to"),
            (r"(.+?)\s+(được thiết kế để|có chức năng)\s+(.+)", "designed_for"),
        ]

    def extract_and_ingest(self, text: str):
        raw_sentences = re.split(r'[.\n;]', text)
        sentences = [s.strip() for s in raw_sentences if s.strip()]
        
        extracted_count = 0
        for sentence in sentences:
            matched = False
            for pattern, relation_type in self.relation_patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    subject = match.group(1).strip()
                    obj = match.group(3).strip()
                    
                    subject_clean = re.sub(r'^(một|các|những|hệ thống|mô hình)\s+', '', subject, flags=re.IGNORECASE)
                    obj_clean = re.sub(r'^(một|các|những|hệ thống|mô hình)\s+', '', obj, flags=re.IGNORECASE)
                    
                    if len(subject_clean) > 1 and len(obj_clean) > 1:
                        self.memory.add_entity(subject_clean, "ExtractedEntity")
                        self.memory.add_entity(obj_clean, "ExtractedEntity")
                        self.memory.add_relation(subject_clean, obj_clean, relation_type)
                        extracted_count += 1
                        matched = True
                        break
            
            if not matched:
                words = [w for w in sentence.split() if len(w) > 3]
                if words:
                    core_concept = " ".join(words[:3])
                    self.memory.add_entity(core_concept, "UnstructuredConcept")
        
        self.memory.save_to_file()
        return extracted_count


class AGIReflectionLoop:
    def __init__(self, memory_system: AGIKnowledgeMemory):
        self.memory = memory_system

    def reflect_and_optimize(self):
        active_nodes = {edge["source"] for edge in self.memory.edges}.union({edge["target"] for edge in self.memory.edges})
        isolated_nodes = [n for n in self.memory.nodes if n not in active_nodes]
        
        pruned_count = 0
        for node_id in isolated_nodes:
            if self.memory.nodes[node_id]["type"] == "UnstructuredConcept":
                del self.memory.nodes[node_id]
                pruned_count += 1
        self.memory.save_to_file()
        return pruned_count


class AGIIntelligenceEngine:
    def __init__(self, memory_system: AGIKnowledgeMemory):
        self.memory = memory_system

    def deep_smart_reasoning(self, start_entity: str, target_entity: str):
        start_entity = start_entity.strip().lower()
        target_entity = target_entity.strip().lower()

        if start_entity not in self.memory.nodes or target_entity not in self.memory.nodes:
            return {"status": "Failed", "message": "Thực thể không tồn tại trong bộ nhớ."}

        adjacency = {}
        for edge in self.memory.edges:
            src, tgt, rel, w = edge["source"], edge["target"], edge["relation"], edge["weight"]
            if src not in adjacency: adjacency[src] = []
            if tgt not in adjacency: adjacency[tgt] = []
            adjacency[src].append((tgt, rel, w, "forward"))
            adjacency[tgt].append((src, rel, w, "backward"))

        pq = [(0, start_entity, [start_entity], [])]
        visited_costs = {start_entity: 0}
        best_path_found = None
        max_accumulated_weight = -1

        while pq:
            neg_cost, current, path, steps = heapq.heappop(pq)
            current_weight_sum = -neg_cost

            if current == target_entity:
                if current_weight_sum > max_accumulated_weight:
                    max_accumulated_weight = current_weight_sum
                    best_path_found = (path, steps)
                continue

            if current not in adjacency: continue

            for neighbor, rel, weight, direction in adjacency[current]:
                if neighbor not in path:
                    new_path = path + [neighbor]
                    new_steps = steps + [{"from": current, "to": neighbor, "relation": rel, "direction": direction, "weight": weight}]
                    new_cost = current_weight_sum + weight

                    if neighbor not in visited_costs or new_cost > visited_costs.get(neighbor, -1):
                        visited_costs[neighbor] = new_cost
                        heapq.heappush(pq, (-new_cost, neighbor, new_path, new_steps))

        if not best_path_found:
            return {"status": "Not Found", "message": "Không tìm thấy chuỗi logic nối giữa hai thực thể này."}

        path_nodes, path_details = best_path_found
        return {
            "status": "Success",
            "path_nodes": path_nodes,
            "total_confidence_score": round(max_accumulated_weight, 2),
            "step_by_step_reasoning": path_details
        }


class AGICuriosityEngine:
    def __init__(self, memory_system: AGIKnowledgeMemory):
        self.memory = memory_system

    def scan_knowledge_gaps(self):
        node_degrees = {node_id: 0 for node_id in self.memory.nodes}
        for edge in self.memory.edges:
            src, tgt = edge["source"], edge["target"]
            if src in node_degrees: node_degrees[src] += 1
            if tgt in node_degrees: node_degrees[tgt] += 1

        gaps = []
        for node_id, degree in node_degrees.items():
            if degree <= 1:
                gaps.append({
                    "entity": node_id,
                    "type": self.memory.nodes[node_id]["type"],
                    "current_connections": degree,
                    "curiosity_score": 5.0 - float(degree)
                })
        gaps.sort(key=lambda x: x["curiosity_score"], reverse=True)
        return gaps

    def trigger_curiosity(self, entity_id: str):
        entity_id = entity_id.strip().lower()
        if entity_id in self.memory.nodes:
            hypo = f"hypothesis_on_{entity_id}"
            self.memory.add_entity(hypo, "AutonomousHypothesis")
            self.memory.add_relation(entity_id, hypo, "explores_potential", weight=3.0)
            self.memory.save_to_file()
            return True
        return False


# ==================== 2. KHỞI TẠO STATE ỨNG DỤNG ====================
if "agi_memory" not in st.session_state:
    st.session_state.agi_memory = AGIKnowledgeMemory()

memory = st.session_state.agi_memory
extractor = AGIKnowledgeExtractor(memory)
reflector = AGIReflectionLoop(memory)
engine = AGIIntelligenceEngine(memory)
curiosity = AGICuriosityEngine(memory)

# ==================== 3. GIAO DIỆN STREAMLIT ====================
st.title("🧠 AGI Cognitive Core Dashboard")
st.markdown("Hệ thống Nhận thức Tự trị: Đồ thị Tri thức, Tự phản xạ, Suy luận Đa bước & Động lực Tự tò mò.")

tab1, tab2, tab3, tab4 = st.tabs(["📥 Nhập liệu & Trích xuất", "📊 Đồ thị Tri thức", "🔍 Suy luận Đa bước", "✨ Động lực Tò mò"])

with tab1:
    st.subheader("Nạp tri thức thô vào AGI")
    raw_input = st.text_area("Nhập văn bản cần phân tích:", "Hệ thống AGI sử dụng Bioacoustics để phân tích âm thanh.\nMô hình Kitsune mô phỏng Sinh vật huyền thoại.\nHệ thống AGI phát triển Mô hình Kitsune.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Trích xuất & Nạp vào Bộ nhớ"):
            count = extractor.extract_and_ingest(raw_input)
            st.success(f"Đã trích xuất và nạp thành công {count} tri thức mới!")
    with col2:
        if st.button("🧠 Kích hoạt Tự phản xạ (Lọc rác)"):
            pruned = reflector.reflect_and_optimize()
            st.warning(f"Đã dọn dẹp và tiêu hủy thành công {pruned} thực thể rác độc lập!")

with tab2:
    st.subheader("Cấu trúc Đồ thị Tri thức (Knowledge Graph)")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"### Tổng thực thể: {len(memory.nodes)}")
        st.json(memory.nodes)
    with col_b:
        st.markdown(f"### Tổng mối quan hệ: {len(memory.edges)}")
        st.json(memory.edges)

with tab3:
    st.subheader("Động cơ Suy luận Thông minh (Multi-step Reasoning)")
    node_list = list(memory.nodes.keys())
    if len(node_list) >= 2:
        start_node = st.selectbox("Chọn thực thể bắt đầu:", node_list, index=0)
        target_node = st.selectbox("Chọn thực thể mục tiêu:", node_list, index=min(1, len(node_list)-1))
        
        if st.button("🔎 Thực hiện Suy luận Đa bước"):
            result = engine.deep_smart_reasoning(start_node, target_node)
            st.json(result)
    else:
        st.info("Vui lòng nạp thêm ít nhất 2 thực thể ở tab Nhập liệu để thực hiện suy luận.")

with tab4:
    st.subheader("Động cơ Tự tò mò & Động lực Nội tại (Curiosity Engine)")
    gaps = curiosity.scan_knowledge_gaps()
    st.markdown(f"**Phát hiện {len(gaps)} khoảng trống tri thức trong hệ thống:**")
    st.dataframe(gaps)
    
    if gaps:
        selected_gap = st.selectbox("Chọn khoảng trống để AGI tự tò mò khám phá:", [g['entity'] for g in gaps])
        if st.button("🎯 Kích hoạt Hành vi Tự tò mò"):
            success = curiosity.trigger_curiosity(selected_gap)
            if success:
                st.success(f"AGI đã tự động thiết lập giả thuyết và mở rộng nhận thức cho '{selected_gap}' thành công!")
                st.rerun() 
