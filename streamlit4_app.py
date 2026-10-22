class Engine:
    def __init__(self, mem):
        self.mem = mem
        self.last = 0
        self.goals = []
        self.progress = {}
        self.uncertainty = {}
        self.source_quality = {"Wiki": 0.7, "DDG": 0.5, "Gemini": 0.6}  # tự điều chỉnh
        self.knowledge_base = {}  # entity -> list thông tin đã có

    def decompose_goal(self, goal_name):
        """Phân rã mục tiêu thành các câu hỏi con đơn giản"""
        subgoals = [
            f"{goal_name} là gì",
            f"{goal_name} có đặc điểm gì",
            f"{goal_name} liên quan đến cái gì"
        ]
        return subgoals

    def check_contradiction(self, entity, new_info):
        """Kiểm tra mâu thuẫn sơ bộ với thông tin cũ"""
        old = self.knowledge_base.get(entity, [])
        if not old:
            return False
        # Đơn giản: nếu thông tin mới quá ngắn hoặc trùng lặp hoàn toàn
        for o in old[-3:]:
            if new_info[:50].lower() in o.lower() or o[:50].lower() in new_info.lower():
                return True  # coi như trùng, không hữu ích thêm
        return False

    def update_source_quality(self, source, was_useful):
        """Điều chỉnh độ tin cậy của nguồn"""
        cur = self.source_quality.get(source, 0.5)
        if was_useful:
            self.source_quality[source] = min(0.95, cur + 0.05)
        else:
            self.source_quality[source] = max(0.2, cur - 0.08)

    def update_uncertainty(self, entity, quality, is_new=True):
        cur = self.uncertainty.get(entity, 1.0)
        if not is_new:
            quality *= 0.3  # thông tin trùng giảm ít hơn
        # Giảm mạnh hơn nếu đã có nhiều thông tin
        count = len(self.knowledge_base.get(entity, []))
        factor = 0.3 / (1 + count * 0.15)
        self.uncertainty[entity] = max(0.05, cur - quality * factor)

    def explore(self, entity):
        self.last = time.time()
        entity = str(entity).strip().lower()
        infos = []

        # Thu thập từ các nguồn, ưu tiên nguồn có quality cao
        sources = sorted(self.source_quality.items(), key=lambda x: -x[1])
        
        for src_name, _ in sources:
            if src_name == "Wiki":
                txt = wiki_search(entity)
            elif src_name == "DDG":
                txt = ddg_search(entity)
            elif src_name == "Gemini" and GEMINI_API_KEY:
                txt = gemini_ask(f"Giải thích ngắn về '{entity}' bằng tiếng Việt.")
            else:
                continue
            if txt and len(txt) > 30:
                infos.append((src_name, txt))

        if not infos:
            return {"ok": False, "msg": "Không tìm được"}

        # Chọn thông tin tốt nhất và kiểm tra trùng
        best_src, best_txt = infos[0]
        is_duplicate = self.check_contradiction(entity, best_txt)
        
        # Lưu
        node_id = f"info_{int(time.time()) % 100000}"
        self.mem.add_entity(node_id, "Thông tin", {
            "src": best_src, "content": best_txt, "about": entity
        })
        self.mem.add_relation(entity, node_id, "có thông tin")
        self.mem.save()

        # Học
        self.knowledge_base.setdefault(entity, []).append(best_txt[:200])
        self.progress[entity] = self.progress.get(entity, 0) + 1
        quality = self.source_quality.get(best_src, 0.5)
        self.update_uncertainty(entity, quality, is_new=not is_duplicate)
        self.update_source_quality(best_src, not is_duplicate)

        # Cập nhật goal
        for g in self.goals:
            if g["name"] == entity and not g["done"]:
                if self.progress.get(entity, 0) >= g["need"] or self.uncertainty.get(entity, 1) < 0.25:
                    g["done"] = True

        return {
            "ok": True,
            "msg": f"{best_src}: {best_txt[:60]}",
            "unc": round(self.uncertainty.get(entity, 1), 2),
            "duplicate": is_duplicate
        }

    def add_goal(self, name, need=3):
        name = str(name).strip().lower()
        if not name or name in [g["name"] for g in self.goals]:
            return
        self.goals.append({"name": name, "need": need, "done": False, "subs": self.decompose_goal(name)})
        self.progress[name] = 0
        self.uncertainty[name] = 1.0
