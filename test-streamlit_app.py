import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Policy Demo", page_icon="⚡", layout="wide")
st.title("⚡ Policy Demo (NumPy)")
st.caption("Mô phỏng Actor-Critic đơn giản")

st.sidebar.header("Cấu hình")
action_space = st.sidebar.slider("Số hành động", 2, 8, 4)
feature_dim = 32

if "W_actor" not in st.session_state:
    rng = np.random.default_rng(42)
    st.session_state.W_actor = rng.normal(0, 0.1, (feature_dim, action_space)).astype(np.float32)
    st.session_state.W_critic = rng.normal(0, 0.1, (feature_dim, 1)).astype(np.float32)
    st.session_state.hidden = np.zeros(feature_dim, dtype=np.float32)

def forward(obs):
    feat = np.tanh(obs[:feature_dim])
    st.session_state.hidden = 0.9 * st.session_state.hidden + 0.1 * feat
    h = st.session_state.hidden
    logits = h @ st.session_state.W_actor
    value = float((h @ st.session_state.W_critic).item())
    # Softmax an toàn
    logits = logits - np.max(logits)
    exp_l = np.exp(logits)
    probs = exp_l / (exp_l.sum() + 1e-8)
    probs = np.clip(probs, 1e-8, 1.0)
    probs = probs / probs.sum()
    action = int(np.random.choice(action_space, p=probs))
    return action, value, logits, probs

tab1, tab2 = st.tabs(["Chạy thử", "Giải thích"])

with tab1:
    if st.button("Thực hiện Forward Pass", use_container_width=True):
        obs = np.random.randn(feature_dim).astype(np.float32)
        action, value, logits, probs = forward(obs)
        c1, c2 = st.columns(2)
        c1.metric("Hành động được chọn", f"Action {action}")
        c2.metric("Value (Critic)", f"{value:.4f}")
        df = pd.DataFrame({
            "Action": [f"Action {i}" for i in range(action_space)],
            "Logits": np.round(logits, 4),
            "Probability": np.round(probs, 4)
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("Reset"):
        st.session_state.hidden = np.zeros(feature_dim, dtype=np.float32)
        st.success("Đã reset trạng thái ẩn")

with tab2:
    st.write("""
    **Code này làm gì?**
    - Tạo một vector quan sát ngẫu nhiên.
    - Qua một lớp đơn giản để ra logits (điểm cho từng hành động).
    - Chuyển logits thành xác suất và chọn 1 hành động.
    - Tính một giá trị Value.
    
    **Không làm gì?**
    - Không học từ dữ liệu.
    - Không tương tác môi trường thật.
    - Không phải ICM hay World Model.
    """)
