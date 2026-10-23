import streamlit as st
import numpy as np
import random
from collections import deque
import time

st.set_page_config(page_title="Intrinsic Motivation Lab", page_icon="🧠", layout="wide")

# ==================== ICM đơn giản bằng NumPy ====================
class SimpleICM:
    def __init__(self, state_dim=6, action_dim=4, feature_dim=16, lr=0.01):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.feature_dim = feature_dim
        self.lr = lr
        # Encoder weights
        self.W_enc = np.random.randn(state_dim, feature_dim).astype(np.float32) * 0.1
        # Forward model: (feature + action_onehot) -> feature
        self.W_fwd = np.random.randn(feature_dim + action_dim, feature_dim).astype(np.float32) * 0.1
        self.memory = deque(maxlen=1000)
        self.eta = 1.0

    def encode(self, s):
        return np.tanh(s @ self.W_enc)

    def onehot(self, a):
        oh = np.zeros(self.action_dim, dtype=np.float32)
        oh[a] = 1.0
        return oh

    def forward_predict(self, feat, action):
        x = np.concatenate([feat, self.onehot(action)])
        return np.tanh(x @ self.W_fwd)

    def intrinsic_reward(self, s, a, ns):
        f = self.encode(s)
        nf = self.encode(ns)
        pred = self.forward_predict(f, a)
        err = np.mean((pred - nf) ** 2)
        return self.eta * err

    def store(self, s, a, r, ns, d):
        self.memory.append((s, a, r, ns, d))

    def update(self, bs=32):
        if len(self.memory) < bs:
            return None
        batch = random.sample(self.memory, bs)
        fwd_losses = []
        for s, a, r, ns, d in batch:
            f = self.encode(s)
            nf = self.encode(ns)
            pred = self.forward_predict(f, a)
            err = pred - nf
            fwd_losses.append(np.mean(err ** 2))
            # Gradient descent đơn giản trên W_fwd
            x = np.concatenate([f, self.onehot(a)])
            grad = np.outer(x, err) * (1 - pred ** 2)  # tanh derivative
            self.W_fwd -= self.lr * grad
        return {"fwd": float(np.mean(fwd_losses)), "icm": float(np.mean(fwd_losses))}

def dummy_step(state_dim=6, action_dim=4):
    s = np.random.randn(state_dim).astype(np.float32) * 0.5
    a = np.random.randint(0, action_dim)
    ns = s.copy()
    ns[a % state_dim] += np.random.uniform(0.4, 0.9)
    ns += np.random.randn(state_dim).astype(np.float32) * 0.05
    return s, a, 0.0, ns, 0.0

# ==================== APP ====================
if "agent" not in st.session_state:
    st.session_state.agent = SimpleICM()
if "logs" not in st.session_state:
    st.session_state.logs = []
if "step_count" not in st.session_state:
    st.session_state.step_count = 0
if "running" not in st.session_state:
    st.session_state.running = False

agent = st.session_state.agent

st.title("🧠 Intrinsic Motivation Lab")
st.caption("Forward Model Prediction Error (NumPy, không cần PyTorch)")

c1, c2, c3 = st.columns(3)
with c1:
    label = "⏸️ Tạm dừng" if st.session_state.running else "🟢 Bắt đầu"
    if st.button(label, use_container_width=True):
        st.session_state.running = not st.session_state.running
        st.rerun()
with c2:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.agent = SimpleICM()
        st.session_state.logs = []
        st.session_state.step_count = 0
        st.session_state.running = False
        st.rerun()
with c3:
    st.metric("Steps", st.session_state.step_count)

st.divider()

with st.expander("Cách hoạt động"):
    st.write("1. Encoder biến trạng thái thành đặc trưng.")
    st.write("2. Forward Model dự đoán đặc trưng của trạng thái kế từ (đặc trưng hiện tại + hành động).")
    st.write("3. Sai số dự đoán = Intrinsic Reward (càng sai càng tò mò).")
    st.write("4. Model được cập nhật để giảm sai số theo thời gian.")

st.subheader("Tiến trình")
if st.session_state.logs:
    last = st.session_state.logs[-1]
    st.metric("Forward Loss (Prediction Error)", f"{last['fwd']:.5f}")
    rows = [{"Step": x["step"], "Forward Loss": round(x["fwd"], 5)} for x in st.session_state.logs[-15:]]
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.info("Nhấn Bắt đầu để huấn luyện.")

st.divider()
if st.button("Thử 1 bước"):
    s, a, r, ns, d = dummy_step()
    ir = agent.intrinsic_reward(s, a, ns)
    agent.store(s, a, r, ns, d)
    stats = agent.update()
    st.write(f"Hành động: {a}")
    st.write(f"Intrinsic Reward (prediction error): **{ir:.5f}**")
    if stats:
        st.success(f"Forward Loss sau update: {stats['fwd']:.5f}")

if st.session_state.running:
    for _ in range(8):
        s, a, r, ns, d = dummy_step()
        agent.store(s, a, r, ns, d)
        st.session_state.step_count += 1
    stats = agent.update(bs=16)
    if stats:
        stats["step"] = st.session_state.step_count
        st.session_state.logs.append(stats)
        st.session_state.logs = st.session_state.logs[-60:]
    time.sleep(0.35)
    st.rerun()
