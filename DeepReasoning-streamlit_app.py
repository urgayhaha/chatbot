# -*- coding: utf-8 -*-
"""
ensemble_free.py — Ensemble Deep Reasoning Agent HOÀN TOÀN MIỄN PHÍ
3 model free cùng giải: Groq (Llama 3.1 70B) + Gemini 1.5 Flash + OpenRouter (Llama 70B free)
Mức suy luận cố định MAX. Chạy: pip install streamlit && streamlit run ensemble_free.py
Lấy key free: console.groq.com | aistudio.google.com | openrouter.ai
"""

import streamlit as st
import json
import re
import time
import threading
import urllib.request
from abc import ABC, abstractmethod

MAX_BRANCHES = 5
MAX_TOP_K = 3
MAX_DEPTH = 8

class LLMBackend(ABC):
    @abstractmethod
    def generate(self, prompt, system="", temperature=0.7, max_tokens=3000):
        pass

def is_error(text):
    return not text or text.startswith("[LLM_ERROR") or len(text.strip()) < 5

class GroqBackend(LLMBackend):
    def __init__(self, api_key, model="llama-3.1-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def generate(self, prompt, system="", temperature=0.7, max_tokens=3000):
        try:
            messages = []
            if system: messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            data = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
            req = urllib.request.Request(self.url, data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}'})
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read().decode('utf-8'))
            return res['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"[LLM_ERROR: {e}]"

class GeminiBackend(LLMBackend):
    def __init__(self, api_key, model="gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    def generate(self, prompt, system="", temperature=0.7, max_tokens=3000):
        try:
            full_prompt = (system + "\n\n" + prompt) if system else prompt
            data = {"contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
            req = urllib.request.Request(self.url, data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read().decode('utf-8'))
            return res['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            return f"[LLM_ERROR: {e}]"

class OpenRouterBackend(LLMBackend):
    def __init__(self, api_key, model="meta-llama/llama-3.1-70b-instruct:free"):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def generate(self, prompt, system="", temperature=0.7, max_tokens=3000):
        try:
            messages = []
            if system: messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            data = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
            req = urllib.request.Request(self.url, data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.api_key}', 'HTTP-Referer': 'https://localhost'})
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read().decode('utf-8'))
            return res['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"[LLM_ERROR: {e}]"

SYSTEM_DEEP = "Bạn là nhà lý luận siêu hạng. Suy luận từng bước, xem xét nhiều hướng, tự kiểm tra lỗi."
DECOMPOSE = "Phân tích đề bài, chia thành tối đa 5 bước con. Đánh số 1. 2. 3.\n\nĐề bài: {problem}\n\nCác bước:"
GENERATE = "Đưa ra {n} HƯỚNG suy luận KHÁC NHAU cho bước hiện tại. Đánh số rõ ràng.\n\nĐề bài: {problem}\nĐã giải: {done}\nBước: {step}\nSuy luận đã có: {prev}\n\n{n} hướng:"
EVALUATE = "Đánh giá độ hứa hẹn (1-10) của hướng này. Chỉ trả về số 1-10.\n\nĐề bài: {problem}\nBước: {step}\nHướng: {thought}\n\nĐiểm:"
VERIFY = "Kiểm tra lời giải có đúng không. Đúng nói 'ĐÚNG', sai chỉ ra lỗi.\n\nĐề bài: {problem}\nLời giải: {solution}\n\nKết luận:"
SYNTHESIZE = "Tổng hợp lời giải CHÍNH XÁC nhất. Trình bày từng bước, đáp án cuối in đậm.\n\nĐề bài: {problem}\nCác hướng: {branches}\n\nLời giải cuối:"
JUDGE = """Dưới đây là 3 lời giải từ 3 AI khác nhau. Đối chiếu, tìm lỗi, đưa ra lời giải CUỐI CÙNG chính xác nhất. Nếu khác nhau, phân tích cái nào đúng. Đáp án cuối in đậm.

Đề bài: {problem}

=== 1. Groq Llama 3.1 70B ===
{sol1}

=== 2. Gemini 1.5 Flash ===
{sol2}

=== 3. OpenRouter Llama 70B ===
{sol3}

Phân tích & Lời giải cuối cùng:
"""

class ToTAgent:
    def __init__(self, llm, name):
        self.llm = llm
        self.name = name
        self.log = []

    def _num(self, text):
        m = re.search(r'(\d+)', text)
        return max(1, min(10, int(m.group(1)))) if m else 5

    def _parse(self, text):
        items = re.split(r'\n\s*(?=\d+[\.\)]\s*)', text)
        items = [re.sub(r'^\d+[\.\)]\s*', '', s).strip() for s in items]
        items = [s for s in items if s and len(s) > 3]
        if not items:
            items = [s.strip() for s in text.split('\n') if s.strip() and len(s.strip()) > 3]
        return items

    def solve(self, problem):
        self.log = [f"### {self.name}"]
        dec = self.llm.generate(DECOMPOSE.format(problem=problem), system=SYSTEM_DEEP, temperature=0.3)
        if is_error(dec): return None, [f"❌ Lỗi {self.name}: {dec}"]
        steps = self._parse(dec)[:MAX_DEPTH] or [problem]
        paths = [{"done": [], "thoughts": [], "score": 0}]
        for step in steps:
            expanded = []
            for p in paths:
                gen = self.llm.generate(GENERATE.format(
                    problem=problem, n=MAX_BRANCHES,
                    done=" | ".join(p["done"]) or "(chưa có)", step=step,
                    prev=" | ".join(p["thoughts"]) or "(chưa có)"),
                    system=SYSTEM_DEEP, temperature=0.8)
                if is_error(gen): continue
                branches = self._parse(gen)[:MAX_BRANCHES] or [gen[:500]]
                for b in branches:
                    ev = self.llm.generate(EVALUATE.format(problem=problem, step=step, thought=b),
                        system="Chỉ trả về số 1-10.", temperature=0.1)
                    sc = self._num(ev)
                    expanded.append((sc, b, {"done": p["done"]+[step], "thoughts": p["thoughts"]+[b], "score": p["score"]+sc}))
            if not expanded: break
            expanded.sort(key=lambda x: -x[0])
            paths = [p for _,_,p in expanded[:MAX_TOP_K]]
        best = None
        for p in paths:
            sol = "\n".join(p["thoughts"])
            v = self.llm.generate(VERIFY.format(problem=problem, solution=sol), system=SYSTEM_DEEP, temperature=0.2)
            if "ĐÚNG" in v.upper() and (best is None or p["score"] > best["score"]):
                best = p
        if best is None and paths: best = paths[0]
        if best is None: return None, self.log
        summary = "\n\n".join("\n".join(p["thoughts"]) for p in paths)
        final = self.llm.generate(SYNTHESIZE.format(problem=problem, branches=summary), system=SYSTEM_DEEP, temperature=0.3)
        if is_error(final): final = "\n".join(best["thoughts"])
        return final, self.log

def solve_ensemble(problem, groq_key, gemini_key, openrouter_key):
    backends = {}
    if groq_key: backends["Groq Llama 70B"] = GroqBackend(groq_key)
    if gemini_key: backends["Gemini 1.5 Flash"] = GeminiBackend(gemini_key)
    if openrouter_key: backends["OpenRouter Llama 70B"] = OpenRouterBackend(openrouter_key)
    if not backends: return None, {}, {}, "Chưa nhập API key nào!"
    results, logs = {}, {}
    def worker(name, llm):
        agent = ToTAgent(llm, name)
        ans, log = agent.solve(problem)
        results[name] = ans
        logs[name] = log
    threads = [threading.Thread(target=worker, args=(n, b)) for n, b in backends.items()]
    for t in threads: t.start()
    for t in threads: t.join()
    valid = {n: results[n] for n in results if results[n] and not is_error(results[n])}
    if not valid: return None, logs, results, "Tất cả model đều lỗi. Kiểm tra API key."
    judge_name = "Groq Llama 70B" if "Groq Llama 70B" in valid else list(valid.keys())[0]
    judge = backends[judge_name]
    names = list(valid.keys())
    judge_prompt = JUDGE.format(problem=problem,
        sol1=valid.get(names[0], "(lỗi)"),
        sol2=valid.get(names[1], "(không có)") if len(names)>1 else "(không có)",
        sol3=valid.get(names[2], "(không có)") if len(names)>2 else "(không có)")
    final = judge.generate(judge_prompt, system=SYSTEM_DEEP, temperature=0.3, max_tokens=4000)
    if is_error(final): final = list(valid.values())[0]
    return final, logs, results, f"Đã giải bằng {len(valid)}/{len(backends)} model: {', '.join(valid.keys())} | Judge: {judge_name}"

def main():
    st.set_page_config(page_title="🧠 Ensemble Free", layout="wide")
    st.title("🧠 Ensemble Deep Reasoning Agent — HOÀN TOÀN MIỄN PHÍ")
    st.caption("Groq Llama 3.1 70B + Gemini 1.5 Flash + OpenRouter Llama 70B cùng giải. Mức suy luận MAX cố định.")
    with st.sidebar:
        st.header("🔑 API Keys (miễn phí)")
        groq_key = st.text_input("Groq API Key", type="password", help="console.groq.com")
        gemini_key = st.text_input("Google Gemini API Key", type="password", help="aistudio.google.com")
        openrouter_key = st.text_input("OpenRouter API Key", type="password", help="openrouter.ai")
        st.divider()
        st.info(f"⚙️ MAX cố định:\n• {MAX_BRANCHES} hướng/bước\n• Giữ {MAX_TOP_K} nhánh\n• Độ sâu {MAX_DEPTH}")
        if not (groq_key or gemini_key or openrouter_key):
            st.warning("Nhập ít nhất 1 API key.")
    problem = st.text_area("📝 Nhập đề bài:", height=120,
        placeholder="Ví dụ: 3 chiếc hộp (táo/cam/hỗn hợp), tất cả nhãn sai. Mở 1 hộp, lấy 1 quả để xác định cả 3 hộp. Mở hộp nào?")
    if st.button("🚀 Ensemble suy luận (free)", type="primary", use_container_width=True):
        if not problem.strip(): st.error("Nhập đề bài!")
        elif not (groq_key or gemini_key or openrouter_key): st.error("Nhập ít nhất 1 API key!")
        else:
            with st.spinner("🧠 3 model free đang cùng suy luận (1-3 phút)..."):
                start = time.time()
                final, logs, results, status = solve_ensemble(problem, groq_key, gemini_key, openrouter_key)
                elapsed = time.time() - start
            if final is None:
                st.error(f"❌ {status}")
            else:
                st.success(f"✅ {status} | Thời gian: {elapsed:.1f}s")
                with st.expander("📋 Xem lời giải từng model", expanded=False):
                    for name in results:
                        st.subheader(f"🤖 {name}")
                        if logs.get(name):
                            for line in logs[name]: st.text(line)
                        r = results.get(name, "(lỗi)")
                        st.markdown(r if not is_error(r) else f"❌ {r}")
                st.subheader("🎉 Lời giải cuối cùng (judge tổng hợp):")
                st.markdown(final)

if __name__ == "__main__":
    main()
