import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Policy Demo", page_icon="⚡", layout="wide")

st.title("⚡ Policy Demo (NumPy)")
st.caption("Mô phỏng Actor-Critic đơn giản, không cần PyTorch")

# Cấu hình
st.sidebar.header("Cấu hình")
action_space = st.sidebar.slider("Số hành động", 2, 8, 4)
feature_dim = 32

# Khởi tạo trọng số đơn giản
if "W_actor" not in st.session_state:
    st.session_state.W_actor = np.random.randn(feature_dim, action_space).astype(np.float32) * 0.1
    st.session_state.W_critic = np.random.randn(feature_dim, 1).astype(np.float32) * 0.1
    st.session_state.hidden = np.zeros(feature_dim, dtype=np.float32)

def forward(obs_flat):
    """Mô phỏng: obs -> feature -> actor/critic"""
    # Feature giả lập
    feat = np.tanh(obs_flat[:feature_dim] if len(obs_flat) >= feature_dim 
                   else np.pad(obs_flat, (0, feature_dim - len(obs_flat))))
    # Cập nhật hidden đơn giản
    st.session_state.hidden = 0.9 * st.session_state.hidden + 0.1 * feat
    h = st.session_state.hidden
    logits = h @ st.session_state.W_actor
    value = float((h @ st.session_state.W_critic)[0])
    # Softmax
    exp_l = np.exp(logits - np.max(logits))
    probs = exp_l / exp_l.sum()
    action = int(np.random.choice(action_space, p=probs))
    return action, value, logits, probs

tab1, tab2 = st.tabs(["Chạy thử", "Thông tin"])

with tab1:
    st.subheader("Forward Pass")
    if st.button("Thực hiện", use_container_width=True):
        dummy_obs = np.random.randn(feature_dim).astype(np.float32)
        action, value, logits, probs = forward(dummy_obs)

        c1, c2, c3 = st.columns(3)
        c1.metric("Hành động", f"Action {action}")
        c2.metric("Value", f"{value:.4f}")
        c3.metric("Feature dim", feature_dim)

        df = pd.DataFrame({
            "Action": [f"Action {i}" for i in range(action_space)],
            "Logits": logits,
            "Probability": probs
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("Reset trạng thái"):
        st.session_state.hidden = np.zeros(feature_dim, dtype=np.float32)
        st.success("Đã reset")

with tab2:
    st.write("**Đây là mô phỏng đơn giản:**")
    st.write("- Không dùng CNN hay LSTM thật")
    st.write("- Dùng vector ngẫu nhiên thay cho ảnh")
    st.write("- Đủ để thấy luồng: quan sát → xác suất hành động + value")
    st.write("- Chạy được trên Streamlit Cloud mà không cần cài thêm thư viện")
