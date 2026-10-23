import streamlit as st
import numpy as np
import random
from collections import deque
import time

st.set_page_config(page_title="Động lực Nội tại", page_icon="🧠", layout="wide")

# ==================== ICM ====================
class SimpleICM:
    def __init__(self, state_dim=6, action_dim=4, feature_dim=16, lr=0.008):
        self.sd = state_dim
        self.ad = action_dim
        self.fd = feature_dim
        self.lr = lr
        self.W_enc = np.random.randn(state_dim, feature_dim).astype(np.float32) * 0.1
        self.W_fwd = np.random.randn(feature_dim + action_dim, feature_dim).astype(np.float32) * 0.1
        self.memory = deque(maxlen=800)

    def encode(self, s):
        return np.tanh(s @ self.W_enc)

    def oh(self, a):
        v = np.zeros(self.ad, dtype=np.float32)
        v[int(a)] = 1.0
        return v

    def predict(self, f, a):
        return np.tanh(np.concatenate([f, self.oh(a)]) @ self.W_fwd)

    def intr(self, s, a, ns):
        err = self.predict(self.encode(s), a) - self.encode(ns)
        return float(np.mean(err ** 2))

    def store(self, s, a, r, ns, d):
        self.memory.append((np.array(s), int(a), float(r), np.array(ns), float(d)))

    def update(self, bs=24):
        if len(self.memory) < bs:
            return None
        batch = random.sample(self.memory, bs)
        losses = []
        for s, a, r, ns, d in batch:
            f, nf = self.encode(s), self.encode(ns)
            pred = self.predict(f, a)
            err = pred - nf
            losses.append(np.mean(err ** 2))
            x = np.concatenate([f, self.oh(a)])
            self.W_fwd -= self.lr * np.outer(x, err) * (1 - pred ** 2)
        return float(np.mean(losses))

def step(sd=6, ad=4):
    s = np.random.randn(sd).astype(np.float32) * 0.4
    a = np.random.randint(0, ad)
    ns = s.copy()
    ns[a % sd] += np.random.uniform(0.5, 1.0)
    return s, a, 0.0, ns, 0.0

# ==================== TRẠNG THÁI ====================
if "agent" not in st.session_state:
    st.session_state.agent = SimpleICM()
if "logs" not in st.session_state:
    st.session_state.logs = []
if "steps" not in st.session_state:
    st.session_state.steps = 0
if "running" not in st.session_state:
    st.session_state.running = False
if "goals" not in st.session_state:
    st.session_state.goals = []
if "explored" not in st.session_state:
    st.session_state.explored = set()

agent = st.session_state.agent

# ==================== UI ====================
st.title("🧠 Phòng thí nghiệm Động lực Nội tại")

# --- Bảng thống kê ---
st.subheader("Tiến độ các thành phần")
progress_data = [
    ("Tín hiệu tự động (prediction error)", 60),
    ("Tự chọn mục tiêu", 55),
    ("Tự kích hoạt", 65),
    ("Hành động khám phá", 50),
    ("Kết nối bên ngoài", 40),
    ("Học từ kết quả", 45),
    ("Mục tiêu dài hạn", 50),
    ("Giảm sự không chắc chắn", 40),
]
cols = st.columns(4)
for i, (name, pct) in enumerate(progress_data):
    with cols[i % 4]:
        st.metric(name.split("(")[0].strip(), f"{pct}%")
        st.progress(pct / 100)

st.caption("Tổng thể ước lượng: ~50%")
st.divider()

# --- Điều khiển ---
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    if st.button("⏸️ Dừng" if st.session_state.running else "🟢 Bật chạy ngầm", use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
with c2:
    if st.button("🔄 Reset", use_container_width=True):
        for k in ["agent", "logs", "steps", "running", "goals", "explored"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
with c3:
    st.metric("Bước", st.session_state.steps)

# --- Prediction Error ---
st.subheader("Prediction Error (Tín hiệu tò mò)")
if st.session_state.logs:
    st.metric("Forward Loss hiện tại", f"{st.session_state.logs[-1]['loss']:.5f}")
    st.dataframe(
        [{"Bước": x["step"], "Prediction Error": round(x["loss"], 5)} for x in st.session_state.logs[-10:]],
        use_container_width=True, hide_index=True
    )
else:
    st.info("Chưa có dữ liệu. Bật chạy ngầm để bắt đầu.")

# --- Mục tiêu ---
st.subheader("Mục tiêu dài hạn")
gcol1, gcol2 = st.columns([3, 1])
with gcol1:
    new_g = st.text_input("Thêm mục tiêu", label_visibility="collapsed", placeholder="Nhập tên mục tiêu...")
with gcol2:
    if st.button("Thêm", use_container_width=True) and new_g.strip():
        st.session_state.goals.append({"name": new_g.strip(), "done": False, "count": 0})
        st.rerun()

if st.session_state.goals:
    for i, g in enumerate(st.session_state.goals):
        status = "✅" if g["done"] else f"{g['count']}/3"
        st.write(f"{status} — {g['name']}")
else:
    st.caption("Chưa có mục tiêu. Hệ thống có thể tự tạo khi chạy ngầm.")

st.divider()
with st.expander("Giải thích các thành phần"):
    st.write("- **Tín hiệu tự động**: Prediction error của Forward Model.")
    st.write("- **Tự kích hoạt**: Vòng lặp chạy ngầm tự sinh transition và cập nhật.")
    st.write("- **Học từ kết quả**: Loss giảm → model dự đoán tốt hơn.")
    st.write("- **Giảm không chắc chắn**: Error thấp hơn = đã hiểu môi trường hơn.")

# --- Background ---
if st.session_state.running:
    for _ in range(6):
        s, a, r, ns, d = step()
        agent.store(s, a, r, ns, d)
        st.session_state.steps += 1
    loss = agent.update()
    if loss is not None:
        st.session_state.logs.append({"step": st.session_state.steps, "loss": loss})
        st.session_state.logs = st.session_state.logs[-50:]
    # Tự tạo goal đơn giản
    if len(st.session_state.goals) < 3 and st.session_state.steps % 50 == 0:
        st.session_state.goals.append({"name": f"khám phá_{st.session_state.steps}", "done": False, "count": 0})
    time.sleep(0.4)
    st.rerun()
