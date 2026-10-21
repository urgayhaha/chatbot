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

# ==================== 3. WORLD MODEL & PHẢN ỨNG TỰ ĐỘNG ====================
class AGIReactionController:
    def evaluate_and_react(self, risk_score: float, domain: str) -> dict:
        if risk_score >= 0.75:
            return {
                "level": "CRITICAL EMERGENCY",
                "color": "red",
                "action": "EMERGENCY_INTERVENTION",
                "policy": "Kich hoat phanh khan cap, dao huong ne tranh hoac vo hieu hoa tac nhan gay nguy hiem."
            }
        elif risk_score >= 0.40:
            return {
                "level": "WARNING & CAUTION",
                "color": "orange",
                "action": "SLOW_DOWN_AND_MONITOR",
                "policy": "Giam toc do van hanh, tang cuong quan sat cam bien va chuan bi phuong an du phong."
            }
        else:
            return {
                "level": "SAFE OPERATION",
                "color": "green",
                "action": "PROCEED_NORMALLY",
                "policy": "Tiep tuc quy trinh thuc thi chuan, duy tri nhip do on dinh."
            }

class AGIWorldModel:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.reaction_controller = AGIReactionController()

    def simulate_with_ai(self, node_id: str, api_key: str) -> dict:
        if not api_key:
            return {
                "domain": "Fallback Rule",
                "detected_action": "manual_input_required",
                "action_description": "Chua nhap Gemini API Key",
                "predicted_outcome": "Vui long nhap API Key o sidebar de AI phan tich thuc te.",
                "estimated_risk": 0.0,
                "simulated_success": False
            }
        
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Ban la World Model (Mo hinh the gioi vat ly va nhan thuc) cua he thong AGI.
            Hay phan tich tinh huong sau: "{node_id}"
            
            Tra ve ket qua phan tich dung cau truc JSON gom cac truong sau (khong kem markdown thua):
            {{
              "domain": "Physics & Dynamics hoac Cognitive Science",
              "detected_action": "ten hanh dong cot loi bang tieng Anh",
              "action_description": "mo ta ngan gon hanh dong bang tieng Viet",
              "predicted_outcome": "du doan chi tiet he qua vat ly, van toc, quy dao hoac nhan qua bang tieng Viet",
              "estimated_risk": so thuc tu 0.0 den 1.0 danh gia muc do rui ro
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
            
            risk = float(data.get("estimated_risk", 0.0))
            data["reaction"] = self.reaction_controller.evaluate_and_react(risk, data.get("domain", ""))
            
            return data
            
        except Exception as e:
            return {
                "target": node_id,
                "domain": "AI Error",
                "detected_action": "error",
                "action_description": "Loi ket noi hoac xu ly tu Gemini API",
                "predicted_outcome": f"Chi tiet loi: {str(e)}",
                "estimated_risk": 1.0,
                "simulated_success": False,
                "reaction": {"level": "SYSTEM ERROR", "color": "red", "action": "HALT", "policy": "Dung khan cap do loi he thong."}
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
            return {"success": False, "reason": "Khong co muc tieu"}
        target = self.active_goals[0]
        return {"success": True, "target": target, "action": "ai_world_model_active"}

# ==================== 5. KHỞI TẠO TRẠNG THÁI ====================
if "agi_memory" not in st.session_state:
    st.session_state.agi_memory = A
