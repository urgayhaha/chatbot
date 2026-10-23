import streamlit as st
import numpy as np
import random
from collections import deque
import time

st.set_page_config(page_title="Động lực Nội tại", page_icon="🧠", layout="wide")

class SimpleICM:
    def __init__(self):
        self.sd, self.ad, self.fd = 6, 4, 12
        self.lr = 0.01
        self.W_enc = np.random.randn(self.sd, self.fd).astype(np.float32) * 0.1
        self.W_fwd = np.random.randn(self.fd + self.ad, self.fd).astype(np.float32) * 0.1
        self.mem = deque(maxlen=500)

    def enc(self, s):
        return np.tanh(np.asarray(s, dtype=np.float32) @ self.W_enc)

    def pred(self, f, a):
        oh = np.zeros(self.ad, dtype=np.float32)
        oh[int(a)] = 1.0
        return np.tanh(np.concatenate([f, oh]) @ self.W_fwd)

    def error(self, s, a, ns):
        return float(np.mean((self.pred(self.enc(s), a) - self.enc(ns)) ** 2))

    def add(self, s, a, ns):
        self.mem.append((np.array(s), int(a), np.array(ns)))

    def train(self, n=16):
        if len(self.mem) < n:
            return None
        batch = random.sample(self.mem, n)
        losses = []
        for s, a, ns in batch:
            f, nf = self.enc(s), self.enc(ns)
            p = self.pred(f, a)
            e = p - nf
            losses.append(np.mean(e ** 2))
            oh = np.zeros(self.ad, dtype=np.float32)
            oh[a] = 1.0
            x = np.concatenate([f, oh])
            self.W_fwd -= self.lr * np.outer(x, e) * (1 - p ** 2)
        return float(np.mean(losses))

def make_transition():
    s = np.random.randn(6).astype(np.float32) * 0.5
    a = random.randint(0, 3)
    ns = s.copy()
    ns[a % 6] += random.uniform(0.4, 1.0)
    return s, a, ns

# ----- State -----
if "icm" not in st.session_state:
    st.session_state.icm = SimpleICM()
if "history" not in st.session_state:
    st.session_state.history = []
if "n_steps" not in st.session_state:
    st.session_state.n_steps = 0
if "on" not in st.session_state:
    st.session_state.on = False

icm = st.session_state.icm

st.title("Động lực Nội tại")

# Tiến độ
st.write("**Tiến độ thành phần**")
items = [
    ("Tín hiệu dự đoán", 60),
    ("Tự kích hoạt", 65),
    ("Học từ sai số", 50),
    ("Giảm không chắc chắn", 45),
]
cs = st.columns(4)
for col, (name, pct) in zip(cs, items):
    col.metric(name, f"{pct}%")
    col.progress(pct / 100.0)

st.divider()

# Điều khiển
b1, b2, b3 = st.columns([2, 2, 1])
with b1:
    if st.button("Dừng" if st.session_state.on else "Bật chạy", use_container_width=True):
        st.session_state.on = not st.session_state.on
        st.rerun()
with b2:
    if st.button("Reset", use_container_width=True):
        st.session_state.icm = SimpleICM()
        st.session_state.history = []
        st.session_state.n_steps = 0
        st.session_state.on = False
        st.rerun()
with b3:
    st.metric("Bước", st.session_state.n_steps)

# Kết quả
st.subheader("Sai số dự đoán")
hist = st.session_state.history
if len(hist) > 0:
    st.metric("Loss gần nhất", f"{hist[-1]['loss']:.5f}")
    st.dataframe(
        [{"Bước": h["step"], "Loss": round(h["loss"], 5)} for h in hist[-12:]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Chưa có dữ liệu. Nhấn Bật chạy.")

# Chạy nền
if st.session_state.on:
    for _ in range(5):
        s, a, ns = make_transition()
        icm.add(s, a, ns)
        st.session_state.n_steps += 1
    loss = icm.train()
    if loss is not None:
        st.session_state.history.append({"step": st.session_state.n_steps, "loss": loss})
        if len(st.session_state.history) > 40:
            st.session_state.history = st.session_state.history[-40:]
    time.sleep(0.5)
    st.rerun()
