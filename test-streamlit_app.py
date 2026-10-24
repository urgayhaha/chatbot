import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Policy Demo", page_icon="⚡", layout="wide")
st.title("⚡ Policy Demo (NumPy)")
st.caption("Mô phỏng Actor-Critic đơn giản")

st.sidebar.header("Cấu hình")
action_space = st.sidebar.slider("Số hành động", 2, 8, 4)
feature_dim = 32

# Tạo lại trọng số nếu số hành động thay đổi
if "action_space" not in st.session_state or st.session_state.action_space != action_space:
    rng = np.random.default_rng()
    st.session_state.W_actor = rng.normal(0, 0.1, (feature_dim, action_space)).astype(np.float32)
    st.session_state.W_critic = rng.normal(0, 0.1, (feature_dim, 1)).astype(np.float32)
    st.session_state.hidden = np.zeros(feature_dim, dtype=np.float32)
    st.session_state.action_space = action_space

def forward(obs, n_actions):
    feat = np.tanh(obs[:feature_dim])
    st.session_state.hidden = 0.9 * st.session_state.hidden + 0.1 * feat
    h = st.session_state.hidden.astype(np.float32)
    logits = h @ st.session_state.W_actor
    value = float(np.dot(h, st.session_state.W_critic.ravel()))
    # Softmax cực kỳ an toàn
    logits = np.asarray(logits, dtype=np.float64)
    logits = logits - np.max(logits)
    exp_l = np.exp(logits)
    probs = exp_l / np.sum(exp_l)
    # Đảm bảo tổng = 1 và không âm
    probs = np.maximum(probs, 0)
    probs = probs / np.sum(probs)
    action = int(np.random.choice(n_actions, p=probs))
    return action, value, logits.astype(np.float32), probs.astype(np.float32)

if st.button("Thực hiện Forward Pass", use_container_width=True):
    obs = np.random.randn(feature_dim).astype(np.float32)
    action, value, logits, probs = forward(obs, action_space)
    c1, c2 = st.columns(2)
    c1.metric("Hành động được chọn", f"Action {action}")
    c2.metric("Value (Critic)", f"{value:.4f}")
    df = pd.DataFrame({
        "Action": [f"Action {i}" for i in range(action_space)],
        "Logits": np.round(logits, 4),
        "Probability": np.round(probs, 4)
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Tổng xác suất: {probs.sum():.6f}")

if st.button("Reset trạng thái ẩn"):
    st.session_state.hidden = np.zeros(feature_dim, dtype=np.float32)
    st.success("Đã reset")
