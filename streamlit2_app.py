import streamlit as st
import json
import os
import time
import re
import heapq
import pandas as pd
import random
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
        if source not in self.nodes: self.add_entity(source, "Unknown")
        if target not in self.nodes: self.add_entity(target, "Unknown")
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

# ==================== 2. EXTRACTOR & REFLECTION ====================
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
                    if len(sub) > 1 and len(obj) > 1:
                        self.memory.add_entity(sub, "Thực thể chính")
                        self.memory.add_entity(obj, "Thực thể chính")
                        self.memory.add_relation(sub, obj, rel)
                        count += 1
                        matched = True
                        break
            if not matched:
                words = [w for w in sentence.split() if len(w) > 3]
                if words:
                    self.memory.add_entity(" ".join(words[:3]), "Khái niệm thô")
        self.memory.save_to_file()
        return count

class AGIReflectionLoop:
    def __init__(self, memory_system):
        self.memory = memory_system

    def reflect_and_optimize(self):
        active = {e["source"] for e in self.memory.edges} | {e["target"] for e in self.memory.edges}
        pruned = 0
        for nid in list(self.memory.nodes.keys()):
            if nid not in active and self.memory.nodes[nid].get("type") in ["Khái niệm thô", "UnstructuredConcept"]:
                del self.memory.nodes[nid]
                pruned += 1
        self.memory.save_to_file()
        return pruned

# ==================== 3. IMPROVED CURIOSITY ENGINE ====================
class ImprovedCuriosityEngine:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.exploration_history = []

    def compute_curiosity_score(self, node_id: str) -> float:
        if node_id not in self.memory.nodes:
            return 0.0
        node = self.memory.nodes[node_id]
        degree = sum(1 for e in self.memory.edges if e["source"] == node_id or e["target"] == node_id)
        isolation = max(0, 3.0 - degree)
        age = time.time() - node.get("created_at", time.time())
        recency = max(0, 2.0 - age / 3600)
        explored = any(h["target"] == node_id for h in self.exploration_history)
        novelty = 0.0 if explored else 2.0
        type_bonus = 1.5 if node.get("type") in ["Khái niệm thô", "Unknown"] else 0.5
        return isolation + recency + novelty + type_bonus

    def scan_and_rank(self):
        scores = []
        for node_id in self.memory.nodes:
            score = self.compute_curiosity_score(node_id)
            if score > 1.0:
                scores.append({"entity": node_id, "score": round(score, 2),
                               "type": self.memory.nodes[node_id].get("type", "Unknown")})
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores

    def act_on_curiosity(self, entity_id: str) -> dict:
        entity_id = entity_id.strip().lower()
        if entity_id not in self.memory.nodes:
            return {"success": False}
        actions = [self._generate_question, self._seek_related_concept, self._strengthen_weak_link]
        result = random.choice(actions)(entity_id)
        self.exploration_history.append({"target": entity_id, "action": result.get("action"), "timestamp": time.time()})
        self.memory.save_to_file()
        return result

    def _generate_question(self, entity_id: str) -> dict:
        questions = [f"{entity_id} liên quan đến những gì?", f"{entity_id} được dùng để làm gì?"]
        q = random.choice(questions)
        q_node = f"câu_hỏi_{int(time.time())}"
        self.memory.add_entity(q_node, "Câu hỏi khám phá", {"content": q})
        self.memory.add_relation(entity_id, q_node, "cần trả lời", weight=2.0)
        return {"success": True, "action": "generate_question", "detail": q}

    def _seek_related_concept(self, entity_id: str) -> dict:
        candidates = [n for n in self.memory.nodes if n != entity_id]
        if not candidates:
            return {"success": False, "action": "seek_related"}
        related = random.choice(candidates)
        self.memory.add_relation(entity_id, related, "có thể liên quan", weight=1.5)
        return {"success": True, "action": "seek_related", "detail": f"Liên kết với {related}"}

    def _strengthen_weak_link(self, entity_id: str) -> dict:
        weak = [e for e in self.memory.edges if (e["source"] == entity_id or e["target"] == entity_id) and e["weight"] < 2.0]
        if weak:
            random.choice(weak)["weight"] = min(5.0, random.choice(weak)["weight"] + 1.0)
            return {"success": True, "action": "strengthen", "detail": "Tăng weight"}
        hypo = f"giả_thuyết_{int(time.time())}"
        self.memory.add_entity(hypo, "Giả thuyết")
        self.memory.add_relation(entity_id, hypo, "cần kiểm chứng", weight=2.0)
        return {"success": True, "action": "create_hypothesis", "detail": hypo}

    def auto_explore_once(self) -> dict:
        ranked = self.scan_and_rank()
        if not ranked:
            return {"success": False, "reason": "Không có mục tiêu"}
        target = ranked[0]["entity"]
        result = self.act_on_curiosity(target)
        result["target"] = target
        result["curiosity_score"] = ranked[0]["score"]
        return result

# ==================== 4. KHỞI TẠO ====================
if "agi_memory" not in st.session_state:
    st.session_state.agi_memory = AGIKnowledgeMemory()
if "background_running" not in st.session_state:
    st.session_state.background_running = False
if "curiosity_engine" not in st.session_state:
    st.session_state.curiosity_engine = ImprovedCuriosityEngine(st.session_state.agi_memory)
if "explore_log" not in st.session_state:
    st.session_state.explore_log = []

memory = st.session_state.agi_memory
extractor = AGIKnowledgeExtractor(memory)
reflector = AGIReflectionLoop(memory)
curiosity = st.session_state.curiosity_engine

# ==================== 5. SIDEBAR ====================
st.title("🧠 AGI Cognitive Core Dashboard")
st.caption("Bộ nhớ tri thức + Động lực tò mò cải tiến")

st.sidebar.header("⚙️ Điều khiển")
if st.session_state.background_running:
    st.sidebar.markdown("🟢 **ĐANG CHẠY NGẦM**")
    if st.sidebar.button("🛑 Dừng", use_container_width=True):
        st.session_state.background_running = False
        st.rerun()
else:
    st.sidebar.markdown("🔴 **ĐÃ DỪNG**")
    if st.sidebar.button("🟢 Bật chạy ngầm", use_container_width=True):
        st.session_state.background_running = True
        st.rerun()

st.sidebar.divider()
if st.session_state.explore_log:
    st.sidebar.markdown("### Nhật ký khám phá gần nhất")
    for log in st.session_state.explore_log[-5:]:
        st.sidebar.caption(f"• {log}")

# ==================== 6. TABS ====================
tab1, tab2, tab3 = st.tabs(["📥 Nhập liệu", "📊 Đồ thị", "✨ Tò mò"])

with tab1:
    st.subheader("Nạp văn bản")
    raw = st.text_area("Văn bản:", "Hệ thống AGI sử dụng Bioacoustics.\nMô hình Kitsune mô phỏng sinh vật.", height=100)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Trích xuất", use_container_width=True):
            n = extractor.extract_and_ingest(raw)
            st.success(f"Đã nạp {n} liên kết")
            st.rerun()
    with c2:
        if st.button("🧠 Dọn rác", use_container_width=True):
            p = reflector.reflect_and_optimize()
            st.warning(f"Đã xóa {p} node rác")
            st.rerun()

with tab2:
    st.subheader("Đồ thị Tri thức")
    m1, m2 = st.columns(2)
    m1.metric("Nodes", len(memory.nodes))
    m2.metric("Edges", len(memory.edges))
    if memory.edges:
        df = pd.DataFrame([{"Từ": e["source"], "Quan hệ": e["relation"], "Đến": e["target"], "Weight": e["weight"]} for e in memory.edges])
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Động lực Tò mò")
    ranked = curiosity.scan_and_rank()
    if ranked:
        df = pd.DataFrame(ranked)
        st.dataframe(df, use_container_width=True, hide_index=True)
        if st.button("🎯 Khám phá ngay (thủ công)"):
            res = curiosity.auto_explore_once()
            if res.get("success"):
                st.success(f"{res['target']} → {res.get('detail')}")
                st.session_state.explore_log.append(f"{res['target']}: {res.get('detail')}")
                st.rerun()
    else:
        st.info("Không có mục tiêu tò mò hiện tại.")

# ==================== 7. BACKGROUND LOOP ====================
if st.session_state.background_running:
    result = curiosity.auto_explore_once()
    if result.get("success"):
        msg = f"{result['target']} → {result.get('detail', result.get('action'))}"
        st.toast(f"🔍 {msg}")
        st.session_state.explore_log.append(msg)
    time.sleep(4)
    st.rerun()
