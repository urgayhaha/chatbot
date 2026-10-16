import streamlit as st
from groq import Groq
from datetime import datetime
import os

st.set_page_config(page_title="AI Chat", page_icon="🤖", layout="wide")
st.title("🤖 AI Chat (Groq)")
st.caption("Kết nối với Groq - miễn phí và nhanh")

# Lấy API Key từ biến môi trường hoặc Streamlit secrets (không hardcode)
API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")

if not API_KEY:
    st.error("Chưa có Groq API Key. Hãy đặt biến môi trường GROQ_API_KEY hoặc thêm vào Streamlit secrets.")
    st.stop()

client = Groq(api_key=API_KEY)

# Khởi tạo lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Mình là AI dùng Groq. Bạn muốn hỏi gì?"}
    ]

# Hiển thị lịch sử
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Nhận input từ người dùng
if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",  # Model miễn phí, ổn định trên Groq
                    messages=st.session_state.messages,
                    temperature=0.7,
                    max_tokens=1024
                )
                reply = response.choices[0].message.content or ""
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Lỗi: {e}")

st.caption(f"Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}")
