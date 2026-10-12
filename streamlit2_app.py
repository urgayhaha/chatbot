import streamlit as st
from groq import Groq
from datetime import datetime

st.set_page_config(page_title="AI Chat", page_icon="🤖", layout="wide")

st.title("🤖 AI Chat (Groq)")
st.caption("Kết nối với Groq - miễn phí và nhanh")

api_key = st.sidebar.text_input("Groq API Key", type="password")

if not api_key:
    st.info("Vui lòng nhập Groq API Key ở thanh bên trái.")
    st.stop()

client = Groq(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Mình là AI dùng Groq. Bạn muốn hỏi gì?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            try:
                clean_messages = []
                for m in st.session_state.messages:
                    content = str(m["content"]).encode("utf-8", errors="ignore").decode("utf-8")
                    clean_messages.append({"role": m["role"], "content": content})

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=clean_messages,
                    temperature=0.7,
                    max_tokens=1024
                )
                reply = response.choices[0].message.content or ""
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Lỗi: {e}")

st.caption(f"Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}")
