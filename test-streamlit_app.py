# -*- coding: utf-8 -*-
"""
Nova Agent v2 — Agent hoàn chỉnh hơn
- Chat có nhớ hội thoại
- Lưu fact vào memory.json
- Tìm Wikipedia
- Có mục tiêu (goals)
- Có thể bật chế độ tự chạy nền
- Kiểm tra Ollama trước khi dùng

Chạy: python nova_agent_v2.py
"""
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext

MEMORY_FILE = "memory.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"
MAX_HISTORY = 6


class Memory:
    def __init__(self, path=MEMORY_FILE):
        self.path = path
        self.items = []
        self.goals = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                self.items = data.get("items", [])
                self.goals = data.get("goals", [])
            except Exception:
                pass

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"items": self.items, "goals": self.goals}, f, ensure_ascii=False, indent=2)

    def add_item(self, topic, content, source="chat"):
        content = str(content).strip()
        if len(content) < 8:
            return False
        preview = content[:40].lower()
        for it in self.items[-30:]:
            if preview in it.get("content", "").lower():
                return False
        self.items.append({
            "topic": topic[:60],
            "content": content[:500],
            "source": source,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        self.save()
        return True

    def add_goal(self, name):
        name = name.strip().lower()
        if name and not any(g["name"] == name for g in self.goals):
            self.goals.append({"name": name, "done": 0, "finished": False})
            self.save()

    def recall(self, keyword, limit=3):
        kw = keyword.strip().lower()
        if not kw:
            return []
        return [it for it in reversed(self.items)
                if kw in it.get("content", "").lower() or kw in it.get("topic", "").lower()][:limit]

    def active_goals(self):
        return [g for g in self.goals if not g["finished"]]


def check_ollama():
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code != 200:
            return False, "Ollama không trả lời."
        models = [m.get("name", "") for m in r.json().get("models", [])]
        if not any(MODEL in m for m in models):
            return False, f"Chưa có model '{MODEL}'. Chạy: ollama pull {MODEL}"
        return True, "OK"
    except Exception as e:
        return False, f"Không kết nối Ollama: {e}"


def search_wiki(query):
    for lang in ("vi", "en"):
        try:
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ', '_'))}"
            req = urllib.request.Request(url, headers={"User-Agent": "NovaAgent/2.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            extract = data.get("extract", "")
            if len(extract) > 30:
                return data.get("title", query), extract[:400], f"wiki-{lang}"
        except Exception:
            continue
    return None, None, None


def search_duckduckgo(query):
    """Tìm bằng DuckDuckGo Instant Answer API (không cần key)."""
    try:
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        })
        req = urllib.request.Request(url, headers={"User-Agent": "NovaAgent/2.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        abstract = data.get("AbstractText") or data.get("Abstract") or ""
        if len(abstract) > 40:
            title = data.get("Heading") or query
            return title, abstract[:500], "duckduckgo"
        # Fallback: related topics
        topics = data.get("RelatedTopics") or []
        texts = []
        for t in topics[:3]:
            if isinstance(t, dict) and t.get("Text"):
                texts.append(t["Text"][:150])
        if texts:
            return query, " | ".join(texts), "duckduckgo"
    except Exception:
        pass
    return None, None, None


class NovaAgent:
    def __init__(self):
        self.memory = Memory()
        self.history = []
        self.ollama_ok, self.ollama_msg = check_ollama()

    def _call_ollama(self, prompt):
        if not self.ollama_ok:
            return f"(Ollama chưa sẵn sàng: {self.ollama_msg})"
        try:
            import requests
            resp = requests.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False},
                timeout=60
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return f"(Ollama lỗi {resp.status_code})"
        except Exception as e:
            return f"(Lỗi Ollama: {e})"

    def chat(self, user_text):
        text = user_text.strip()
        if not text:
            return ""
        lower = text.lower()

        if lower.startswith("nhớ ") or lower.startswith("lưu "):
            fact = text.split(" ", 1)[1]
            return "Đã lưu." if self.memory.add_item("user", fact) else "Không lưu được."

        if lower.startswith("mục tiêu ") or lower.startswith("goal "):
            g = text.split(" ", 1)[1]
            self.memory.add_goal(g)
            return f"Đã thêm mục tiêu: {g}"

        if lower.startswith("tìm ") or "wiki" in lower or "duck" in lower:
            q = re.sub(r"(tìm|wikipedia|wiki|duckduckgo|duck)", "", lower).strip() or text
            # Ưu tiên DuckDuckGo, nếu không có thì Wikipedia
            title, content, src = search_duckduckgo(q)
            if not content:
                title, content, src = search_wiki(q)
            if content:
                self.memory.add_item(q, content, src or "search")
                return f"[{src}] {title}:\n{content}"
            return "Không tìm thấy trên DuckDuckGo hoặc Wikipedia."

        recalled = self.memory.recall(text)
        mem_ctx = ""
        if recalled:
            mem_ctx = "\nĐã biết:\n" + "\n".join(f"- {r['content'][:100]}" for r in recalled)

        hist = "\n".join(f"{h['role']}: {h['text'][:80]}" for h in self.history[-MAX_HISTORY:])
        prompt = (
            "Bạn là Nova, trợ lý AI tiếng Việt. Trả lời ngắn, rõ, không bịa.\n"
            f"{mem_ctx}\nLịch sử:\n{hist}\nNgười dùng: {text}\nNova:"
        )
        answer = self._call_ollama(prompt)
        self.history.append({"role": "user", "text": text})
        self.history.append({"role": "ai", "text": answer})
        if len(self.history) > 12:
            self.history = self.history[-12:]
        return answer

    def autonomous_step(self):
        """Một bước tự hành động (dùng khi bật nền)."""
        goals = self.memory.active_goals()
        if not goals:
            self.memory.add_goal("trí tuệ nhân tạo")
            return "Tự tạo mục tiêu: trí tuệ nhân tạo"
        goal = goals[0]["name"]
        title, content, src = search_duckduckgo(goal)
        if not content:
            title, content, src = search_wiki(goal)
        if content:
            self.memory.add_item(goal, content, src or "auto")
            return f"Tự tìm [{src}]: {title}"
        return f"Không tìm được thêm về {goal}"


class NovaApp:
    def __init__(self):
        self.agent = NovaAgent()
        self.auto_running = False
        self.root = tk.Tk()
        self.root.title("Nova Agent v2")
        self.root.geometry("860x640")
        self.root.configure(bg="#121212")

        self.chat = scrolledtext.ScrolledText(
            self.root, bg="#121212", fg="#e0e0e0", font=("Segoe UI", 11),
            wrap=tk.WORD, relief="flat", padx=12, pady=12, state=tk.DISABLED
        )
        self.chat.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        bottom = tk.Frame(self.root, bg="#121212")
        bottom.pack(fill=tk.X, padx=8, pady=8)
        self.entry = tk.Entry(bottom, font=("Segoe UI", 11), bg="#1e1e1e",
                              fg="white", insertbackground="white", relief="flat")
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(0, 6))
        self.entry.bind("<Return>", self.send)
        tk.Button(bottom, text="Gửi", command=self.send, bg="#333", fg="white",
                  relief="flat", padx=14).pack(side=tk.RIGHT, padx=(0, 4))
        self.auto_btn = tk.Button(bottom, text="Bật tự chạy", command=self.toggle_auto,
                                  bg="#1f4e79", fg="white", relief="flat", padx=10)
        self.auto_btn.pack(side=tk.RIGHT)

        status = "Ollama OK" if self.agent.ollama_ok else self.agent.ollama_msg
        self.write("system",
                   f"Nova Agent v2 sẵn sàng. ({status})\n"
                   "- nhớ ...   để lưu fact\n"
                   "- mục tiêu ...  để thêm mục tiêu\n"
                   "- tìm ...   để tìm DuckDuckGo rồi Wikipedia\n"
                   "- Nút 'Bật tự chạy' để agent tự tìm khi rảnh")

    def write(self, role, text):
        self.chat.config(state=tk.NORMAL)
        name = {"user": "Bạn", "ai": "Nova", "system": "Hệ thống"}.get(role, role)
        self.chat.insert(tk.END, f"{name}: {text}\n\n")
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    def send(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self.write("user", text)
        threading.Thread(target=self.handle, args=(text,), daemon=True).start()

    def handle(self, text):
        ans = self.agent.chat(text)
        self.root.after(0, lambda: self.write("ai", ans))

    def toggle_auto(self):
        self.auto_running = not self.auto_running
        self.auto_btn.config(text="Tắt tự chạy" if self.auto_running else "Bật tự chạy")
        if self.auto_running:
            self.write("system", "Đã bật tự chạy nền.")
            threading.Thread(target=self.auto_loop, daemon=True).start()
        else:
            self.write("system", "Đã tắt tự chạy.")

    def auto_loop(self):
        while self.auto_running:
            time.sleep(25)
            if not self.auto_running:
                break
            msg = self.agent.autonomous_step()
            self.root.after(0, lambda m=msg: self.write("system", m))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    NovaApp().run()
