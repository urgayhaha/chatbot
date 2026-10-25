# -*- coding: utf-8 -*-
"""
deep_reasoning_agent.py — Deep Reasoning Agent (Tree-of-Thoughts + Self-Verification)
Chạy trên Streamlit. Giải bài toán từ đầu, không cần dữ liệu trước.
Hỗ trợ Ollama local + OpenAI API (kể cả o1/o3).
Chạy: pip install streamlit && streamlit run deep_reasoning_agent.py
"""

import streamlit as st
import json
import re
import time
import urllib.request
from abc import ABC, abstractmethod

# ============================================================================
# LLM BACKENDS
# ============================================================================
class LLMBackend(ABC):
    @abstractmethod
    def generate(self, prompt, system="", temperature=0.7, max_tokens=2500):
        pass

def is_error(text):
    return not text or text.startswith("[LLM_ERROR") or len(text.strip()) < 5

class OllamaBackend(LLMBackend):
    def __init__(self, model="llama3", url="http://localhost:11434/api/generate"):
        self.model = model
        self.url = url

    def generate(self, prompt, system="", temperature=0.7, max_tokens=2500):
        try:
            data = {"model": self.model, "prompt": prompt, "system": system,
                    "stream": False, "options": {"temperature": temperature, "num_predict": max_tokens}}
            req = urllib.request.Request(self.url, data=json.dumps(data).encode('utf-8'),
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=180) as r:
                res = json.loads(r.read().decode('utf-8'))
            return res.get('response', '').strip()
        except Exception as e:
            return f"[LLM_ERROR: {e}]"

class OpenAIBackend(LLMBackend):
    def __init__(self, api_key, model="gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"

    def generate(self, prompt, system="", temperature=0.7, max_tokens=2500):
        try:
            messages = []
            is_reasoning_model = self.model.startswith(("o1", "o3", "o4"))
            if system and not is_reasoning_model:
                messages.append({"role": "system", "content": system})
            if is_reasoning_model and system:
                prompt = system + "\n\n" + prompt
            messages.append({"role": "user", "content": prompt})
            data = {"model": self.model, "messages": messages}
            if is_reasoning_model:
                data["max_completion_tokens"] = max_tokens
            else:
                data["temperature"] = temperature
                data["max_tokens"] = max_tokens
            req = urllib.request.Request(self.url, data=json.dumps(data).encode('utf-8'),
                                         headers={'Content-Type': 'application/json',
                                                  'Authorization': f'Bearer {self.api_key}'})
            with urllib.request.urlopen(req, timeout=300) as r:
                res = json.loads(r.read().decode('utf-8'))
            return res['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"[LLM_ERROR: {e}]"

# ============================================================================
# PROMPTS
# ============================================================================
SYSTEM_DEEP = """Bạn là một nhà lý luận siêu hạng. Bạn luôn suy luận từng bước, xem xét nhiều hướng, tự kiểm tra lỗi, và không bao giờ bỏ qua chi tiết. Khi không chắc chắn, bạn thử nhiều phương pháp và đối chiếu kết quả."""

DECOMPOSE_PROMPT = """Phân tích đề bài sau và chia thành các bước con cần giải quyết (tối đa 5 bước). Liệt kê từng bước ngắn gọn, đánh số 1. 2. 3.

Đề bài: {problem}

Các bước:"""

GENERATE_PROMPT = """Bạn đang giải bài toán sau. Hãy đưa ra {n} HƯỚNG suy luận KHÁC NHAU cho bước hiện tại. Mỗi hướng phải là một cách tiếp cận khác nhau. Đánh số 1. 2. 3. rõ ràng.

Đề bài: {problem}
Các bước đã giải: {done_steps}
Bước hiện tại: {current_step}
Suy luận đã có: {previous_thoughts}

{n} hướng suy luận khác nhau:"""

EVALUATE_PROMPT = """Đánh giá độ hứa hẹn (1-10) của hướng suy luận sau. Chỉ trả về một số nguyên 1-10, không giải thích.

Đề bài: {problem}
Bước: {step}
Hướng suy luận: {thought}

Điểm:"""

VERIFY_PROMPT = """Kiểm tra lời giải sau có đúng không. Tìm lỗi logic, tính toán sai, hoặc giả định không hợp lệ. Nếu có lỗi, chỉ ra cụ thể. Nếu đúng, nói "ĐÚNG".

Đề bài: {problem}
Lời giải: {solution}

Kết luận:"""

SYNTHESIZE_PROMPT = """Từ các hướng suy luận đã kiểm tra, tổng hợp thành lời giải cuối cùng CHÍNH XÁC nhất. Trình bày rõ ràng, từng bước, nêu đáp án cuối cùng in đậm.

Đề bài: {problem}
Các hướng đã thử (kèm đánh giá): {branches_summary}

Lời giải cuối cùng:"""

# ============================================================================
# TREE-OF-THOUGHTS AGENT
# ============================================================================
class ToTAgent:
    def __init__(self, llm, num_branches=3, top_k=2, max_depth=5):
        self.llm = llm
        self.num_branches = max(1, int(num_branches))
        self.top_k = max(1, int(top_k))
        self.max_depth = max(1, int(max_depth))
        self.log = []

    def _log(self, msg):
        self.log.append(msg)

    def _extract_number(self, text):
        m = re.search(r'(\d+)', text)
        if m:
            n = int(m.group(1))
            return max(1, min(10, n))
        return 5

    def _parse_numbered_list(self, text):
        items = re.split(r'\n\s*(?=\d+[\.\)]\s*)', text)
        items = [re.sub(r'^\d+[\.\)]\s*', '', s).strip() for s in items]
        items = [s for s in items if s and len(s) > 3]
        if not items:
            items = [s.strip() for s in text.split('\n') if s.strip() and len(s.strip()) > 3]
        return items

    def solve(self, problem):
        self.log = []
        self._log(f"### 🎯 Đề bài: {problem}")

        self._log("\n--- 🔬 BƯỚC 1: Phân tích đề bài & chia nhỏ ---")
        decompose = self.llm.generate(DECOMPOSE_PROMPT.format(problem=problem),
                                      system=SYSTEM_DEEP, temperature=0.3)
        if is_error(decompose):
            self._log(f"❌ Lỗi LLM khi phân tích: {decompose}")
            return None, self.log
        self._log(decompose)
        steps = self._parse_numbered_list(decompose)[:self.max_depth]
        if not steps:
            steps = [problem]
        self._log(f"→ Chia thành {len(steps)} bước con.")

        self._log("\n--- 🌳 BƯỚC 2: Tree-of-Thoughts ---")
        active_paths = [{"steps_done": [], "thoughts": [], "score": 0}]

        for step_idx, step in enumerate(steps):
            self._log(f"\n**Bước {step_idx+1}/{len(steps)}: {step}**")
            expanded = []
            for path in active_paths:
                done = " | ".join(path["steps_done"]) if path["steps_done"] else "(chưa có)"
                prev = " | ".join(path["thoughts"]) if path["thoughts"] else "(chưa có)"
                gen_prompt = GENERATE_PROMPT.format(
                    problem=problem, done_steps=done, current_step=step,
                    previous_thoughts=prev, n=self.num_branches)
                gen_result = self.llm.generate(gen_prompt, system=SYSTEM_DEEP, temperature=0.8)
                if is_error(gen_result):
                    self._log(f"  ⚠️ Lỗi sinh hướng: {gen_result[:100]}")
                    continue
                branches = self._parse_numbered_list(gen_result)[:self.num_branches]
                if not branches:
                    branches = [gen_result[:500]]
                self._log(f"  → Sinh {len(branches)} hướng suy luận.")

                for i, branch in enumerate(branches):
                    eval_result = self.llm.generate(
                        EVALUATE_PROMPT.format(problem=problem, step=step, thought=branch),
                        system="Chỉ trả về một số nguyên 1-10.", temperature=0.1)
                    score = self._extract_number(eval_result)
                    new_path = {
                        "steps_done": path["steps_done"] + [step],
                        "thoughts": path["thoughts"] + [branch],
                        "score": path["score"] + score
                    }
                    expanded.append((score, branch, new_path))
                    self._log(f"    Hướng {i+1} (điểm {score}/10): {branch[:120]}...")

            if not expanded:
                self._log("  ❌ Không sinh được hướng nào, dừng sớm.")
                break
            expanded.sort(key=lambda x: -x[0])
            active_paths = [p for _, _, p in expanded[:self.top_k]]
            self._log(f"  → Giữ {len(active_paths)} hướng tốt nhất.")

        self._log("\n--- 🛡️ BƯỚC 3: Self-Verification ---")
        best_solution = None
        best_score = -1
        for idx, path in enumerate(active_paths):
            solution = "\n".join(path["thoughts"])
            verify = self.llm.generate(VERIFY_PROMPT.format(problem=problem, solution=solution),
                                       system=SYSTEM_DEEP, temperature=0.2)
            self._log(f"Kiểm tra hướng {idx+1} (tổng điểm {path['score']}): {verify[:200]}")
            if "ĐÚNG" in verify.upper() and path["score"] > best_score:
                best_solution = solution
                best_score = path["score"]

        if not best_solution and active_paths:
            best_solution = "\n".join(active_paths[0]["thoughts"])
            self._log("⚠️ Không hướng nào ĐÚNG, chọn hướng điểm cao nhất.")

        self._log("\n--- ✅ BƯỚC 4: Tổng hợp lời giải cuối ---")
        summary = "\n\n".join([f"Hướng {i+1} (tổng điểm {p['score']}):\n" + "\n".join(p["thoughts"])
                               for i, p in enumerate(active_paths)])
        final = self.llm.generate(SYNTHESIZE_PROMPT.format(problem=problem, branches_summary=summary),
                                  system=SYSTEM_DEEP, temperature=0.3)
        if is_error(final):
            final = best_solution or "Không thể tổng hợp lời giải."
        self._log(f"\n## 🎉 LỜI GIẢI CUỐI CÙNG:\n\n{final}")
        return final, self.log

# ============================================================================
# STREAMLIT UI
# ============================================================================
def main():
    st.set_page_config(page_title="🧠 Deep Reasoning Agent", layout="wide")
    st.title("🧠 Deep Reasoning Agent — Tree-of-Thoughts + Self-Verification")
    st.caption("Agent suy luận sâu: sinh nhiều hướng → đánh giá → cắt tỉa → tự kiểm tra → tự sửa lỗi.")

    with st.sidebar:
        st.header("⚙️ Cấu hình")
        provider = st.selectbox("LLM Backend", ["Ollama (local)", "OpenAI API"])
        llm = None
        if provider == "Ollama (local)":
            model = st.text_input("Ollama Model", value="llama3")
            ollama_url = st.text_input("Ollama URL", value="http://localhost:11434/api/generate")
            llm = OllamaBackend(model=model, url=ollama_url)
        else:
            api_key = st.text_input("OpenAI API Key", type="password")
            model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1-preview", "o3-mini"])
            if api_key:
                llm = OpenAIBackend(api_key=api_key, model=model)
            else:
                st.warning("Nhập API key để dùng OpenAI.")

        st.divider()
        num_branches = st.slider("Số hướng suy luận mỗi bước", 2, 5, 3)
        top_k = st.slider("Giữ lại N hướng tốt nhất", 1, 3, 2)
        max_depth = st.slider("Độ sâu tối đa", 2, 8, 5)

    problem = st.text_area("📝 Nhập đề bài cần giải:", height=120,
                           placeholder="Ví dụ: Một cửa hàng bán áo giá 200k, giảm 20% còn rẻ hơn 50k so với giá gốc. Tìm giá gốc?")

    if st.button("🚀 Bắt đầu suy luận sâu", type="primary", use_container_width=True):
        if not problem.strip():
            st.error("Nhập đề bài trước!")
        elif llm is None:
            st.error("Cấu hình LLM backend trước!")
        else:
            agent = ToTAgent(llm, num_branches=num_branches, top_k=top_k, max_depth=max_depth)
            with st.spinner("🧠 Đang suy luận sâu (có thể mất 1-5 phút)..."):
                start = time.time()
                final_answer, log = agent.solve(problem)
                elapsed = time.time() - start

            if final_answer is None:
                st.error("❌ Lỗi: Không thể kết nối LLM. Kiểm tra Ollama đang chạy hoặc API key.")
            else:
                with st.expander("📋 Xem toàn bộ quá trình suy luận", expanded=False):
                    for line in log:
                        if line.startswith("###") or line.startswith("**"):
                            st.markdown(line)
                        elif line.startswith("---"):
                            st.markdown(f"**{line.strip('- ')}**")
                        else:
                            st.text(line)

                st.success(f"✅ Hoàn thành trong {elapsed:.1f}s")
                st.subheader("🎉 Lời giải cuối cùng:")
                st.markdown(final_answer)

if __name__ == "__main__":
    main()
