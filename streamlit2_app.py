import random
import time

class ImprovedCuriosityEngine:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.exploration_history = []  # lưu những gì đã khám phá
    
    def compute_curiosity_score(self, node_id: str) -> float:
        """Tín hiệu tò mò tốt hơn: kết hợp nhiều yếu tố"""
        if node_id not in self.memory.nodes:
            return 0.0
        
        node = self.memory.nodes[node_id]
        
        # 1. Ít liên kết → tò mò hơn
        degree = sum(1 for e in self.memory.edges 
                     if e["source"] == node_id or e["target"] == node_id)
        isolation_score = max(0, 3.0 - degree)
        
        # 2. Mới tạo gần đây → tò mò hơn
        age = time.time() - node.get("created_at", time.time())
        recency_score = max(0, 2.0 - age / 3600)  # giảm dần theo giờ
        
        # 3. Chưa từng được khám phá → tò mò hơn
        explored = any(h["target"] == node_id for h in self.exploration_history)
        novelty_score = 0.0 if explored else 2.0
        
        # 4. Loại node đặc biệt
        type_bonus = 1.5 if node.get("type") in ["Khái niệm thô", "Unknown"] else 0.5
        
        return isolation_score + recency_score + novelty_score + type_bonus
    
    def scan_and_rank(self):
        """Quét và xếp hạng tất cả node theo điểm tò mò"""
        scores = []
        for node_id in self.memory.nodes:
            score = self.compute_curiosity_score(node_id)
            if score > 1.0:  # ngưỡng tối thiểu
                scores.append({
                    "entity": node_id,
                    "score": round(score, 2),
                    "type": self.memory.nodes[node_id].get("type", "Unknown")
                })
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores
    
    def act_on_curiosity(self, entity_id: str) -> dict:
        """Hành động tò mò có ý nghĩa hơn"""
        entity_id = entity_id.strip().lower()
        if entity_id not in self.memory.nodes:
            return {"success": False, "reason": "Node không tồn tại"}
        
        actions = [
            self._generate_question,
            self._seek_related_concept,
            self._strengthen_weak_link,
        ]
        
        # Chọn hành động ngẫu nhiên (có thể thay bằng chính sách thông minh hơn)
        action_fn = random.choice(actions)
        result = action_fn(entity_id)
        
        # Ghi lại lịch sử khám phá
        self.exploration_history.append({
            "target": entity_id,
            "action": result.get("action"),
            "timestamp": time.time()
        })
        
        self.memory.save_to_file()
        return result
    
    def _generate_question(self, entity_id: str) -> dict:
        """Sinh câu hỏi về thực thể"""
        questions = [
            f"{entity_id} liên quan đến những gì khác?",
            f"{entity_id} được dùng để làm gì?",
            f"Có khái niệm nào tương tự {entity_id} không?",
        ]
        question = random.choice(questions)
        
        q_node = f"câu_hỏi_{int(time.time())}"
        self.memory.add_entity(q_node, "Câu hỏi khám phá", {"content": question})
        self.memory.add_relation(entity_id, q_node, "cần trả lời", weight=2.0)
        
        return {"success": True, "action": "generate_question", "detail": question}
    
    def _seek_related_concept(self, entity_id: str) -> dict:
        """Tìm khái niệm liên quan từ các node hiện có"""
        candidates = [n for n in self.memory.nodes if n != entity_id]
        if not candidates:
            return {"success": False, "action": "seek_related", "detail": "Không có node khác"}
        
        related = random.choice(candidates)
        self.memory.add_relation(entity_id, related, "có thể liên quan", weight=1.5)
        
        return {"success": True, "action": "seek_related", "detail": f"Liên kết với {related}"}
    
    def _strengthen_weak_link(self, entity_id: str) -> dict:
        """Tăng cường liên kết yếu nếu có"""
        weak_edges = [e for e in self.memory.edges 
                      if (e["source"] == entity_id or e["target"] == entity_id) 
                      and e["weight"] < 2.0]
        
        if weak_edges:
            edge = random.choice(weak_edges)
            edge["weight"] = min(5.0, edge["weight"] + 1.0)
            return {"success": True, "action": "strengthen", "detail": f"Tăng weight liên kết"}
        else:
            # Không có liên kết yếu → tạo giả thuyết
            hypo = f"giả_thuyết_{int(time.time())}"
            self.memory.add_entity(hypo, "Giả thuyết")
            self.memory.add_relation(entity_id, hypo, "cần kiểm chứng", weight=2.0)
            return {"success": True, "action": "create_hypothesis", "detail": hypo}
    
    def auto_explore_once(self) -> dict:
        """Một vòng khám phá tự động"""
        ranked = self.scan_and_rank()
        if not ranked:
            return {"success": False, "reason": "Không có mục tiêu tò mò"}
        
        target = ranked[0]["entity"]
        result = self.act_on_curiosity(target)
        result["target"] = target
        result["curiosity_score"] = ranked[0]["score"]
        return result
