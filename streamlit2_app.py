import streamlit as st
import json
import os
import time
import re
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

# ==================== 2. EXTRACTOR ====================
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

# ==================== 3. REFLECTION ====================
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

# ==================== 4. CURIOSITY ENGINE (thang 0-10) ====================
class ImprovedCuriosityEngine:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.exploration_history = []
        self.hypothesis_count = {}
        self.node_visit_count = {}
        self.last_exploration_time = {}

    def compute_curiosity_score(self, node_id: str) -> dict:
        if node_id not in self.memory.nodes:
            return {"total": 0.0}
        node = self.memory.nodes[node_id]
        node_type = node.get("type", "")
        if node_type in ["Giả thuyết", "Câu hỏi khám phá", "Giả thuyết tự chủ"]:
            return {"total": 0.0}

        scores = {}
        degree = sum(1 for e in self.memory.edges if e["source"] == node_id or e["target"] == node_id)
        scores["isolation"] = max(0.0, 3.0 - degree * 0.8)

        age_hours = (time.time() - node.get("created_at", time.time())) / 3600
        scores["recency"] = max(0.0, 2.0 * (1.0 - min(age_hours / 24, 1.0)))

        times_explored = self.node_visit_count.get(node_id, 0)
        scores["novelty"] = 2.5 if times_explored == 0 else max(0, 1.5 - times_explored * 0.5)

        last_time = self.last_exploration_time.get(node_id, 0)
        hours_since = (time.time() - last_time) / 3600 if last_time > 0 else 24
        scores["staleness"] = min(2.0, hours_since / 6)

        scores["type_bonus"] = 1.5 if node_type in ["Khái niệm thô", "Unknown", ""] else 0.5

        weak_links = sum(1 for e in self.memory.edges
                         if (e["source"] == node_id or e["target"] == node_id) and e["weight"] < 2.0)
        scores["weak_links"] = min(1.5, weak_links * 0.5)

        raw_total = sum(scores.values())
        if node_id in self.last_exploration_time and time.time() - self.last_exploration_time[node_id] < 120:
            raw_total *= 0.3

        # Chuẩn hóa về thang 0-10 (max lý thuyết = 12.5)
        scores["total"] = round(min(10.0, max(0.0, raw_total / 1.25)), 2)
        return scores

    def scan_and_rank(self, top_k=10):
        results = []
        for node_id in self.memory.nodes:
            detail = self.compute_curiosity_score(node_id)
            total = detail.get("total", 0)
            if total > 0.8:
                results.append({
                    "entity": node_id,
                    "score": total,
                    "type": self.memory.nodes[node_id].get("type", "Unknown"),
                    "breakdown": {k: round(v, 2) for k, v in detail.items() if k != "total"}
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def select_target(self, ranked: list):
        if not ranked:
            return None
        recent = [h["target"] for h in self.exploration_history[-5:]]
        candidates = [r for r in ranked if r["entity"] not in recent]
        if not candidates:
            candidates = ranked
        return random.choice(candidates[:3])["entity"]

    def should_explore(self) -> bool:
        ranked = self.scan_and_rank()
        if not ranked or ranked[0]["score"] < 1.6:
            return False
        if self.exploration_history and time.time() - self.exploration_history[-1]["timestamp"] < 8:
            return False
        return True

    def act_on_curiosity(self, entity_id: str) -> dict:
        entity_id = entity_id.strip().lower()
        if entity_id not in self.memory.nodes:
            return {"success": False}
        self.node_visit_count[entity_id] = self.node_visit_count.get(entity_id, 0) + 1
        self.last_exploration_time[entity_id] = time.time()

        hypo_count = self.hypothesis_count.get(entity_id, 0)
        actions = [self._seek_related_concept, self._strengthen_weak_link] if hypo_count >= 2 else \
                  [self._seek_related_concept, self._generate_question, self._strengthen_weak_link]
        result = random.choice(actions)(entity_id)
        if result.get("action") == "create_hypothesis":
            self.hypothesis_count[entity_id] = hypo_count + 1
        self.exploration_history.append({"target": entity_id, "action": result.get("action"), "timestamp": time.time()})
        self.memory.save_to_file()
        return result

    def _generate_question(self, entity_id: str) -> dict:
        questions = [f"{entity_id} liên quan đến những khái niệm nào khác?",
                     f"{entity_id} có chức năng gì?",
                     f"Có thể kết hợp {entity_id} với cái gì?"]
        q = random.choice(questions)
        q_node = f"câu_hỏi_{int(time.time()) % 100000}"
        self.memory.add_entity(q_node, "Câu hỏi khám phá", {"content": q})
        self.memory.add_relation(entity_id, q_node, "cần trả lời", weight=2.0)
        return {"success": True, "action": "generate_question", "detail": q}

    def _seek_related_concept(self, entity_id: str) -> dict:
        candidates = [n for n, info in self.memory.nodes.items()
                      if n != entity_id and info.get("type") not in ["Giả thuyết", "Câu hỏi khám phá", "Giả thuyết tự chủ"]]
        if not candidates:
            return {"success": False, "action": "seek_related"}
        related = random.choice(candidates)
        exists = any((e["source"] == entity_id and e["target"] == related) or
                     (e["source"] == related and e["target"] == entity_id) for e in self.memory.edges)
        if not exists:
            self.memory.add_relation(entity_id, related, "có thể liên quan", weight=1.5)
            return {"success": True, "action": "seek_related", "detail": f"Liên kết với {related}"}
        return {"success": False, "action": "seek_related"}

    def _strengthen_weak_link(self, entity_id: str) -> dict:
        weak = [e for e in self.memory.edges if (e["source"] == entity_id or e["target"] == entity_id) and e["weight"] < 3.0]
        if weak:
            edge = random.choice(weak)
            edge["weight"] = min(5.0, edge["weight"] + 0.5)
            return {"success": True, "action": "strengthen", "detail": f"Tăng weight '{edge['relation']}'"}
        if self.hypothesis_count.get(entity_id, 0) < 2:
            hypo = f"giả_thuyết_{int(time.time()) % 100000}"
            self.memory.add_entity(hypo, "Giả thuyết")
            self.memory.add_relation(entity_id, hypo, "cần kiểm chứng", weight=2.0)
            return {"success": True, "action": "create_hypothesis", "detail": hypo}
        return {"success": False, "action": "none"}

    def auto_explore_once(self) -> dict:
        if not self.should_explore():
            return {"success": False, "reason": "Chưa đến lúc"}
        ranked = self.scan_and_rank()
        target = self.select_target(ranked)
        if not target:
            return {"success": False}
        result = self.act_on_curiosity(target)
        result["target"] = target
        result["curiosity_score"] = next((r["score"] for r in ranked if r["entity"] == target), 0)
        return result

    def cleanup_old_hypotheses(self, max_age_seconds=600):
        now = time.time()
        to_delete = [nid for nid, info in self.memory.nodes.items()
                     if info.get("type") in ["Giả thuyết", "Câu hỏi khám phá"]
                     and now - info.get("created_at", now) > max_age_seconds]
        for nid in to_delete:
            del self.memory.nodes[nid]
            self.memory.edges = [e for e in self.memory.edges if e["source"] != nid and e["target"] != nid]
        if to_delete:
            self.memory.save_to_file()
        return len(to_delete)

# ==================== 5. KHỞI TẠO ====================
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

# ==================== 6. GIAO DIỆN ====================
st.title("🧠 AGI Cognitive Core Dashboard")
st.caption("Curiosity Score (thang 0–10)")

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
    st.sidebar.markdown("### Nhật ký")
    for log in reversed(st.session_state.explore_log[-6:]):
        st.sidebar.caption(f"• {log}")

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
            st.warning(f"Đã xóa {p}")
            st.rerun()

with tab2:
    c1, c2 = st.columns(2)
    c1.metric("Nodes", len(memory.nodes))
    c2.metric("Edges", len(memory.edges))
    if memory.edges:
        df = pd.DataFrame([{"Từ": e["source"], "Quan hệ": e["relation"], "Đến": e["target"], "W": round(e["weight"], 1)} for e in memory.edges])
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Curiosity Score (0–10)")
    ranked = curiosity.scan_and_rank()
    if ranked:
        for item in ranked[:8]:
            with st.expander(f"**{item['entity']}** — {item['score']}/10"):
                st.write(f"Loại: `{item.get('type')}`")
                if item.get("breakdown"):
                    st.json(item["breakdown"])
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🎯 Khám phá ngay", use_container_width=True):
                res = curiosity.auto_explore_once()
                if res.get("success"):
                    msg = f"{res.get('target')} → {res.get('detail','')}"
                    st.success(msg)
                    st.session_state.explore_log.append(msg)
                    st.rerun()
        with c2:
            if st.button("🗑️ Dọn giả thuyết", use_container_width=True):
                n = curiosity.cleanup_old_hypotheses()
                st.warning(f"Đã xóa {n}")
                st.rerun()
    else:
        st.info("Không có mục tiêu hiện tại.")

# ==================== 7. BACKGROUND ====================
if st.session_state.background_running:
    result = curiosity.auto_explore_once()
    if result.get("success"):
        msg = f"{result.get('target')} → {result.get('detail','')}"
        st.toast(f"🔍 {msg}")
        st.session_state.explore_log.append(msg)
    time.sleep(5)
    st.rerun()
