import streamlit as st
from groq import Groq
from datetime import datetime

st.set_page_config(page_title="AI Chat", page_icon="🤖", layout="wide")

st.title("🤖 AI Chat (Groq)")
st.caption("Kết nối với Groq - miễn phí và nhanh")

# Nhập API Key (hoặc dùng st.secrets)
api_key = st.sidebar.text_input("Groq API Key", type="password", help="Lấy key miễn phí tại console.groq.com")

if not api_key:
    st.info("Vui lòng nhập Groq API Key ở thanh bên trái để bắt đầu.")
    st.stop()

# Khởi tạo client Groq
client = Groq(api_key=api_key)

# Lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Mình là AI dùng Groq. Bạn muốn hỏi gì?"}
    ]

# Hiển thị tin nhắn
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Ô nhập
if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gọi Groq
    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",  # model mạnh và miễn phí
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                    temperature=0.7,
                    max_tokens=1024
                )
                reply = response.choices[0].message.content
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Lỗi: {e}")

st.caption(f"Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}")
