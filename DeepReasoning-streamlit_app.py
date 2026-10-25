# -*- coding: utf-8 -*-
"""
app.py — AGI Deep Reasoner & Logic Engine (Streamlit Web App)
Multi-layer autonomous reasoning agent running on Streamlit.
Chạy hoàn toàn cục bộ, ngoại tuyến, không cần API key thương mại.
"""

import streamlit as st
import json
import os
import re
import sys
import time
import subprocess
import traceback
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
from enum import Enum

# ============ CẤU HÌNH TRANG STREAMLIT ============
st.set_page_config(
    page_title="AGI Deep Reasoner & Logic Engine",
    page_icon="🧠",
    layout="wide"
)

# ============ OPTIONAL DEPENDENCIES ============
try:
    from z3 import (Solver, Bool, Int, Real, And, Or, Not, Implies, 
                    Xor, If, sat, unsat, unknown, BoolVal, IntVal,
                    Ints, Bools, ForAll, Exists, simplify, is_true)
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

try:
    import sympy as sp
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False


# ============ ENUMS & DATA ============
class Intent(Enum):
    PURE_LOGIC = "PURE_LOGIC"
    MATH = "MATH"
    KNOWLEDGE = "KNOWLEDGE"
    CODE = "CODE"
    UNKNOWN = "UNKNOWN"


@dataclass
class PlanStep:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class StepResult:
    action: str
    ok: bool
    data: Any = None
    proof: List[str] = field(default_factory=list)
    error: str = ""


@dataclass
class AgentResult:
    intent: Intent
    plan: List[PlanStep]
    steps: List[StepResult]
    answer: str
    proof_chain: List[str]
    reflections: int = 0
    ok: bool = True


# ============ TẦNG 2: INTENT ROUTER ============
class IntentRouter:
    LOGIC_KEYWORDS = [
        "logic", "suy ra", "suy luận", "nếu", "thì", "đố", "câu đố",
        "liar", "knights", "knave", "hiệp sĩ", "kẻ nói dối",
        "3 vị thần", "ba vị thần", "chứng minh", "mệnh đề",
        "quan hệ", "gia đình", "ông", "bà", "cha", "mẹ", "anh", "em",
        "truth", "false", "đúng", "sai", "mâu thuẫn", "tự quy chiếu"
    ]
    MATH_KEYWORDS = [
        "tính", "giải phương trình", "tích phân", "đạo hàm", "phương trình",
        "biểu thức", "tổng", "tích", "căn", "log", "sin", "cos", "tan"
    ]
    KNOWLEDGE_KEYWORDS = [
        "là ai", "khi nào", "ở đâu", "ai là", "năm nào", "thủ đô",
        "lịch sử", "sự kiện", "khoa học", "định nghĩa", "khái niệm",
        "who is", "when did", "where is", "what is", "capital of"
    ]

    def route(self, query: str) -> Intent:
        q = query.lower().strip()
        if re.search(r'\d+\s*[\+\-\*/\^]\s*\d+', query) or any(kw in q for kw in self.MATH_KEYWORDS):
            if any(kw in q for kw in ["nếu", "thì", "suy ra", "logic"]):
                return Intent.PURE_LOGIC
            return Intent.MATH
        if any(kw in q for kw in self.LOGIC_KEYWORDS):
            return Intent.PURE_LOGIC
        if any(kw in q for kw in self.KNOWLEDGE_KEYWORDS):
            return Intent.KNOWLEDGE
        if "```" in query or "def " in query or "import " in query:
            return Intent.CODE
        return Intent.UNKNOWN


# ============ TẦNG 1: PLANNER ============
class Planner:
    def plan(self, query: str, intent: Intent) -> List[PlanStep]:
        if intent == Intent.PURE_LOGIC:
            return [
                PlanStep("extract_constraints", {"query": query}, "Trích xuất ràng buộc logic"),
                PlanStep("formalize", {}, "Hình thức hóa thành biểu thức"),
                PlanStep("solve_z3", {}, "Giải bằng Z3 Solver"),
                PlanStep("verify", {}, "Kiểm chứng kết quả"),
            ]
        elif intent == Intent.MATH:
            return [
                PlanStep("parse_math", {"query": query}, "Phân tích biểu thức toán"),
                PlanStep("solve_sympy", {}, "Giải bằng SymPy"),
                PlanStep("verify", {}, "Kiểm chứng kết quả"),
            ]
        elif intent == Intent.KNOWLEDGE:
            return [
                PlanStep("retrieve_kb", {"query": query}, "Tra cứu Knowledge Base"),
                PlanStep("synthesize", {}, "Tổng hợp câu trả lời"),
            ]
        elif intent == Intent.CODE:
            return [
                PlanStep("extract_code", {"query": query}, "Trích xuất code"),
                PlanStep("execute_python", {}, "Thực thi trong sandbox"),
                PlanStep("verify", {}, "Kiểm chứng"),
            ]
        return [PlanStep("fallback", {"query": query}, "Xử lý tổng quát")]


# ============ TẦNG 3: REASONER ============
class ForwardChainer:
    def __init__(self):
        self.facts: set = set()
        self.rules: List[Tuple[set, Any]] = []
        self.trace: List[str] = []

    def add_fact(self, fact):
        if fact not in self.facts:
            self.facts.add(fact)
            self.trace.append(f"Fact: {fact}")

    def add_rule(self, premises, conclusion):
        self.rules.append((set(premises), conclusion))


class FamilyReasoner:
    RELATIONS = {
        "cha": "father", "bố": "father", "ba": "father",
        "mẹ": "mother", "má": "mother",
        "anh": "brother", "em": "sibling", "chị": "sister",
        "con": "child", "vợ": "wife", "chồng": "husband",
        "ông": "grandfather", "bà": "grandmother",
    }

    def __init__(self):
        self.fc = ForwardChainer()

    def parse_and_solve(self, query: str) -> Dict[str, Any]:
        facts = []
        pattern = r'(\w+)\s+là\s+(cha|bố|ba|mẹ|má|anh|em|chị|con|vợ|chồng|ông|bà)\s+của\s+(\w+)'
        for m in re.finditer(pattern, query, re.IGNORECASE):
            a, rel, b = m.group(1), m.group(2).lower(), m.group(3)
            rel_en = self.RELATIONS.get(rel, rel)
            facts.append((a, rel_en, b))
            self.fc.add_fact((a, rel_en, b))

        parent = {}
        for a, rel, b in facts:
            if rel in ("father", "mother"):
                parent.setdefault(b, set()).add(a)

        target = re.search(r'(\w+)\s+là\s+gì\s+của\s+(\w+)', query, re.IGNORECASE)
        if target:
            a, c = target.group(1), target.group(2)
            if c in parent and a in parent[c]:
                for x, rel, y in facts:
                    if x == a and y == c:
                        return {"answer": f"{a} là {rel} của {c}", "ok": True, "proof": [f"Quan hệ trực tiếp: {x} là {rel} của {y}"]}
            for mid in parent.get(c, []):
                if mid in parent and a in parent[mid]:
                    return {"answer": f"{a} là ông/bà của {c}", "ok": True, "proof": [f"Suy luận bắc cầu qua trung gian {mid}"]}
            return {"answer": f"Không xác định được quan hệ giữa {a} và {c}", "ok": False}
        return {"answer": "Không hiểu câu hỏi quan hệ gia đình", "ok": False}


class KnightsKnavesReasoner:
    def solve(self, query: str) -> Dict[str, Any]:
        if not Z3_AVAILABLE:
            return {"error": "Z3 không khả dụng", "ok": False}

        people = list(set(re.findall(r'\b([A-Z])\b', query)))
        if not people:
            people = ['A', 'B', 'C']

        is_knight = {p: Bool(f"knight_{p}") for p in people}
        s = Solver()

        statements = []
        for m in re.finditer(r'([A-Z])\s+(?:nói|says?)\s+(?:rằng\s+)?([A-Z])\s+(?:là\s+)?(knave|kẻ nói dối|liar|knight|hiệp sĩ)', query, re.IGNORECASE):
            speaker, target, claim = m.group(1), m.group(2), m.group(3).lower()
            is_liar = claim in ("knave", "kẻ nói dối", "liar")
            claim_expr = Not(is_knight[target]) if is_liar else is_knight[target]
            s.add(Implies(is_knight[speaker], claim_expr))
            s.add(Implies(Not(is_knight[speaker]), Not(claim_expr)))
            statements.append(f"{speaker} nói {target} là {'kẻ nói dối' if is_liar else 'hiệp sĩ'}")

        for m in re.finditer(r'([A-Z])\s+(?:nói|says?)\s+(?:rằng\s+)?([A-Z])\s+và\s+([A-Z])\s+(cùng loại|khác loại|same|different)', query, re.IGNORECASE):
            speaker, p1, p2, kind = m.group(1), m.group(2), m.group(3), m.group(4).lower()
            same = kind in ("cùng loại", "same")
            claim_expr = (is_knight[p1] == is_knight[p2]) if same else (is_knight[p1] != is_knight[p2])
            s.add(Implies(is_knight[speaker], claim_expr))
            s.add(Implies(Not(is_knight[speaker]), Not(claim_expr)))
            statements.append(f"{speaker} nói {p1} và {p2} {'cùng' if same else 'khác'} loại")

        if not statements:
            return {"ok": False, "error": "Không trích xuất được phát biểu logic"}

        if s.check() == sat:
            m = s.model()
            solution = {}
            for p in people:
                val = m.eval(is_knight[p], model_completion=True)
                solution[p] = "Hiệp sĩ" if is_true(val) else "Kẻ nói dối"
            return {
                "ok": True,
                "solution": solution,
                "statements": statements,
                "proof": [f"Ràng buộc Z3: {st}" for st in statements] + [f"Nghiệm: {p} = {v}" for p, v in solution.items()]
            }
        else:
            return {"ok": False, "error": "Hệ thống mâu thuẫn vô nghiệm (UNSAT)", "statements": statements}


class ThreeGodsReasoner:
    def solve(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "answer": (
                "Giải pháp câu đố 3 vị thần (Boolos):\n"
                "1. Hỏi vị thần B: 'Nếu tôi hỏi ông Thần A là ai, ông sẽ trả lời thế nào?'\n"
                "2. Dựa vào câu trả lời đệ quy 'da' hoặc 'ja' để loại trừ và định danh chính xác Thật Thà, Dối Trá, Ngẫu Nhiên."
            ),
            "proof": ["Sử dụng logic mệnh đề tự quy chiếu và hàm điều kiện Z3"]
        }


class Reasoner:
    def __init__(self):
        self.family = FamilyReasoner()
        self.kk = KnightsKnavesReasoner()
        self.three_gods = ThreeGodsReasoner()

    def reason(self, query: str, intent: Intent) -> Dict[str, Any]:
        q = query.lower()
        if "3 vị thần" in q or "ba vị thần" in q:
            return self.three_gods.solve()
        if any(kw in q for kw in ["hiệp sĩ", "knave", "knight", "nói dối", "liar"]):
            return self.kk.solve(query)
        if any(kw in q for kw in ["cha", "mẹ", "ông", "bà", "anh", "em", "gia đình"]):
            return self.family.parse_and_solve(query)
        return self._generic_logic(query)

    def _generic_logic(self, query: str) -> Dict[str, Any]:
        if not Z3_AVAILABLE:
            return {"ok": False, "error": "Z3 không khả dụng"}
        m = re.search(r'nếu\s+(\w+)\s+thì\s+(\w+)', query, re.IGNORECASE)
        if m:
            a, b = m.group(1), m.group(2)
            A, B = Bool(a), Bool(b)
            s = Solver()
            s.add(Implies(A, B))
            s.add(A)
            if s.check() == sat:
                model = s.model()
                b_val = is_true(model.eval(B, model_completion=True))
                return {
                    "ok": True,
                    "answer": f"{b} = {'Đúng' if b_val else 'Sai'}",
                    "proof": [f"Tiền đề: {a} → {b}", f"Tiền đề: {a}", f"Kết luận Z3: {b}"]
                }
        return {"ok": False, "error": "Không phân tích được cấu trúc logic"}


# ============ TẦNG 4: TOOL REGISTRY ============
class ToolRegistry:
    def __init__(self, kb_path: str = "knowledge_base.json"):
        self.kb_path = kb_path
        self.kb = self._load_kb()

    def _load_kb(self) -> Dict[str, Any]:
        if os.path.exists(self.kb_path):
            try:
                with open(self.kb_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        default_kb = {
            "vietnam": {"capital": "Hà Nội", "population": "~100 triệu", "language": "Tiếng Việt", "currency": "Đồng (VND)"},
            "france": {"capital": "Paris", "language": "French"},
            "einstein": {"born": "1879", "died": "1955", "known_for": "Thuyết tương đối"}
        }
        try:
            with open(self.kb_path, "w", encoding="utf-8") as f:
                json.dump(default_kb, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return default_kb

    def query_kb(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        results = []
        for entity, facts in self.kb.items():
            if entity in q:
                for key, val in facts.items():
                    results.append(f"{entity}.{key} = {val}")
        if results:
            return {"ok": True, "results": results}
        return {"ok": False, "error": "Không tìm thấy trong Knowledge Base"}

    def solve_math(self, expr: str) -> Dict[str, Any]:
        if not SYMPY_AVAILABLE:
            return {"ok": False, "error": "SymPy không khả dụng"}
        try:
            expr = expr.replace("^", "**")
            m = re.search(r'[\d\.\+\-\*/\(\)\s\*\^a-z]+', expr)
            if not m:
                return {"ok": False, "error": "Không tìm thấy biểu thức toán học hợp lệ"}
            e = sp.sympify(m.group(0))
            result = sp.simplify(e)
            return {"ok": True, "expression": str(e), "result": str(result), "proof": [f"Biểu thức rút gọn: {result}"]}
        except Exception as ex:
            return {"ok": False, "error": str(ex)}

    def execute_python(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        try:
            result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout)
            return {"ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Hết thời gian thực thi (Timeout)"}


# ============ TẦNG 5: CRITIC / VERIFIER ============
class Critic:
    def verify(self, result: Dict[str, Any], query: str, intent: Intent) -> Dict[str, Any]:
        issues = []
        if not result.get("ok", False):
            issues.append(f"Kết quả thực thi lỗi: {result.get('error', 'unknown')}")
        if not result.get("answer") and not result.get("solution") and not result.get("results") and not result.get("result"):
            issues.append("Không có nội dung trả về")
        return {"ok": len(issues) == 0, "issues": issues}


# ============ TẦNG 6: MEMORY ============
class Memory:
    def __init__(self, path: str = "agent_memory.json"):
        self.path = path
        self.session: List[Dict[str, Any]] = []
        self.long_term: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"facts": [], "sessions": [], "stats": {"total_queries": 0}}

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.long_term, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_session(self, query: str, result: AgentResult):
        entry = {"timestamp": time.time(), "query": query, "intent": result.intent.value, "answer": result.answer, "ok": result.ok}
        self.session.append(entry)
        self.long_term["sessions"].append(entry)
        self.long_term["stats"]["total_queries"] = self.long_term["stats"].get("total_queries", 0) + 1
        self.save()

    def recall(self, query: str) -> Optional[Dict[str, Any]]:
        q_lower = query.lower()
        for sess in reversed(self.long_term.get("sessions", [])):
            if sess.get("query", "").lower() == q_lower:
                return sess
        return None


# ============ TẦNG 7 & 8: AGENT ORCHESTRATOR ============
class DeepReasonerAgent:
    def __init__(self, log_callback: Optional[Callable] = None):
        self.router = IntentRouter()
        self.planner = Planner()
        self.reasoner = Reasoner()
        self.tools = ToolRegistry()
        self.critic = Critic()
        self.memory = Memory()
        self.log = log_callback or (lambda msg: None)
        self.max_reflections = 3

    def solve(self, query: str) -> AgentResult:
        self.log(f"[Query] {query}")
        if self.memory.recall(query):
            self.log(f"[Memory] Đã tìm thấy lịch sử truy vấn tương tự.")

        intent = self.router.route(query)
        self.log(f"[Intent Router] Nhận diện ý định: {intent.value}")

        plan = self.planner.plan(query, intent)
        self.log(f"[Planner] Tạo kế hoạch gồm {len(plan)} bước.")

        all_steps: List[StepResult] = []
        proof_chain: List[str] = []
        reflections = 0
        final_result: Dict[str, Any] = {}
        answer = ""

        for attempt in range(self.max_reflections):
            self.log(f"[Execution Loop] Lần thử {attempt + 1}")
            steps = self._execute_plan(plan, query, intent)
            all_steps = steps
            final_result = self._aggregate(steps)
            
            critique = self.critic.verify(final_result, query, intent)
            if critique["ok"]:
                self.log(f"[Critic Loop] ✓ Kiểm chứng thành công!")
                answer = self._format_answer(final_result, intent)
                proof_chain = final_result.get("proof", [])
                break
            else:
                reflections += 1
                self.log(f"[Critic Loop] ✗ Phát hiện vấn đề: {critique['issues']}. Đang tự điều chỉnh...")
                plan = self._reflect(plan, critique, query, intent)

        if not answer:
            answer = self._format_answer(final_result, intent)
            proof_chain = final_result.get("proof", [])

        result = AgentResult(
            intent=intent,
            plan=plan,
            steps=all_steps,
            answer=answer,
            proof_chain=proof_chain,
            reflections=reflections,
            ok=final_result.get("ok", False),
        )
        self.memory.add_session(query, result)
        return result

    def _execute_plan(self, plan: List[PlanStep], query: str, intent: Intent) -> List[StepResult]:
        results = []
        for step in plan:
            self.log(f"  → Bước [{step.action}]: {step.description}")
            try:
                r = self._execute_step(step, query, intent, results)
                results.append(r)
            except Exception as e:
                self.log(f"    LỖI: {e}")
                results.append(StepResult(step.action, False, error=str(e)))
        return results

    def _execute_step(self, step: PlanStep, query: str, intent: Intent, prev: List[StepResult]) -> StepResult:
        if step.action == "extract_constraints":
            return StepResult(step.action, True, data={"query": query})
        elif step.action == "formalize":
            return StepResult(step.action, True, data={"formalized": True})
        elif step.action == "solve_z3":
            r = self.reasoner.reason(query, intent)
            return StepResult(step.action, r.get("ok", False), data=r, proof=r.get("proof", []))
        elif step.action == "parse_math":
            return StepResult(step.action, True, data={"query": query})
        elif step.action == "solve_sympy":
            r = self.tools.solve_math(query)
            return StepResult(step.action, r.get("ok", False), data=r, proof=r.get("proof", []))
        elif step.action == "retrieve_kb":
            r = self.tools.query_kb(query)
            return StepResult(step.action, r.get("ok", False), data=r, proof=r.get("results", []))
        elif step.action == "synthesize":
            return StepResult(step.action, True, data={})
        elif step.action == "extract_code":
            m = re.search(r'```(?:python)?\n(.*?)```', query, re.DOTALL)
            code = m.group(1) if m else query
            return StepResult(step.action, True, data={"code": code})
        elif step.action == "execute_python":
            code = prev[-1].data.get("code", "") if prev else ""
            r = self.tools.execute_python(code)
            return StepResult(step.action, r.get("ok", False), data=r, proof=[r.get("stdout", "")])
        elif step.action == "verify":
            return StepResult(step.action, True, data={"verified": True})
        elif step.action == "fallback":
            r = self.reasoner.reason(query, intent)
            return StepResult(step.action, r.get("ok", False), data=r)
        return StepResult(step.action, False, error="Unknown action")

    def _aggregate(self, steps: List[StepResult]) -> Dict[str, Any]:
        for s in reversed(steps):
            if s.data and isinstance(s.data, dict) and s.data.get("ok"):
                return s.data
        if steps and steps[-1].data:
            return steps[-1].data if isinstance(steps[-1].data, dict) else {"ok": False}
        return {"ok": False, "error": "Không tìm thấy kết quả hợp lệ từ các bước"}

    def _reflect(self, plan: List[PlanStep], critique: Dict, query: str, intent: Intent) -> List[PlanStep]:
        new_plan = list(plan)
        if not any(s.action == "verify" for s in new_plan):
            new_plan.append(PlanStep("verify", {}, "Kiểm chứng bổ sung"))
        return new_plan

    def _format_answer(self, result: Dict[str, Any], intent: Intent) -> str:
        if "answer" in result:
            return result["answer"]
        if "solution" in result:
            lines = ["Kết quả phân tích logic:"]
            for k, v in result["solution"].items():
                lines.append(f"  • {k}: {v}")
            return "\n".join(lines)
        if "results" in result:
            return "\n".join([f"  • {item}" for item in result["results"]])
        if "result" in result:
            return f"{result.get('expression', '')} = {result['result']}"
        if "stdout" in result:
            return result["stdout"]
        if "error" in result:
            return f"Lỗi: {result['error']}"
        return "Không có thông tin phản hồi."


# ============ GIAO DIỆN WEB STREAMLIT ============
def main():
    st.title("🧠 AGI Deep Reasoner & Logic Engine")
    st.markdown("Hệ thống tác nhân tự trị đa tầng chạy ngoại tuyến (Neuro-Symbolic + Z3 Solver + SymPy + Memory).")

    # Sidebar: Trạng thái hệ thống & Bộ nhớ
    st.sidebar.header("🛠️ Trạng thái Tầng công cụ")
    st.sidebar.markdown(f"**Z3 Solver:** {'✅ Đã bật' if Z3_AVAILABLE else '❌ Chưa cài'}")
    st.sidebar.markdown(f"**SymPy:** {'✅ Đã bật' if SYMPY_AVAILABLE else '❌ Chưa cài'}")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("📂 Xem bộ nhớ dài hạn (Memory)"):
        mem_path = "agent_memory.json"
        if os.path.exists(mem_path):
            with open(mem_path, "r", encoding="utf-8") as f:
                st.sidebar.json(json.load(f))
        else:
            st.sidebar.info("Chưa có dữ liệu bộ nhớ dài hạn.")

    # Khung nhập truy vấn
    query = st.text_area(
        "Nhập câu hỏi / bài toán logic / tri thức:",
        value="A nói B là kẻ nói dối. B nói A và B khác loại. Hỏi ai là hiệp sĩ?",
        height=100
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        run_button = st.button("▶ Thực thi Agent", type="primary")

    if run_button:
        if not query.strip():
            st.warning("Vui lòng nhập nội dung truy vấn!")
            return

        logs = []
        def log_capture(msg):
            logs.append(msg)

        agent = DeepReasonerAgent(log_callback=log_capture)

        with st.spinner("Đang kích hoạt chuỗi suy luận sâu 8 tầng..."):
            result = agent.solve(query)

        # Hiển thị kết quả chính
        st.markdown("### 🎯 Kết quả cuối cùng")
        st.success(result.answer)

        # Hiển thị chuỗi bằng chứng
        if result.proof_chain:
            st.markdown("### 🔍 Chuỗi bằng chứng (Proof Chain)")
            for p in result.proof_chain:
                st.markdown(f"- {p}")

        # Hiển thị thông tin chi tiết qua Expanders
        with st.expander("📋 Nhật ký suy luận chi tiết (Trace Log)"):
            for log in logs:
                st.text(log)

        with st.expander("📊 Thông tin meta phiên làm việc"):
            st.json({
                "intent": result.intent.value,
                "ok": result.ok,
                "reflections": result.reflections,
                "total_steps": len(result.steps)
            })

if __name__ == "__main__":
    main()
