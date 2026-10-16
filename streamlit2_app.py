import streamlit as st
import threading
import time
import queue

# 1. Cấu hình giao diện Streamlit
st.set_page_config(page_title="Background AI Agent", page_icon="🤖", layout="wide")
st.title("🤖 Trợ lý AI Xử lý Nền (Background Agent)")
st.caption("Ứng dụng minh họa cách chạy tác vụ AI nặng dưới nền mà không làm khóa UI.")

# 2. Khởi tạo hàng đợi (Queue) để giao tiếp giữa luồng nền và Streamlit
if "log_queue" not in st.session_state:
    st.session_state.log_queue = queue.Queue()
if "ai_status" not in st.session_state:
    st.session_state.ai_status = "Đang rảnh"
if "ai_running" not in st.session_state:
    st.session_state.ai_running = False
if "ai_logs" not in st.session_state:
    st.session_state.ai_logs = []

# 3. Hàm giả lập tác vụ AI nặng chạy dưới nền (Background Task)
def heavy_ai_task(prompt, q):
    try:
        q.put("[HỆ THỐNG] Đang khởi tạo World Model và nạp không gian tiềm ẩn...")
        time.sleep(2)  # Giả lập load model
        
        q.put(f"[SUY NGHĨ] Đang bóc tách Prompt: '{prompt}'")
        time.sleep(3)  # Giả lập phân tích nhân quả (Causal Inference)
        
        q.put("[LẬP KẾ HOẠCH] Đang chạy MCTS trên không gian trừu tượng để tìm giải pháp...")
        time.sleep(4)  # Giả lập lập kế hoạch dài hạn
        
        q.put("[BỘ NHỚ] Đang đồng bộ hóa tri thức mới vào bộ nhớ dài hạn (Neural ODEs)...")
        time.sleep(3)
        
        q.put("[KẾT QUẢ] AI đã hoàn thành tác vụ xuất sắc! 🎉")
    except Exception as e:
        q.put(f"[LỖI] Đã xảy ra sự cố: {str(e)}")

# 4. Giao diện điều khiển
col1, col2 = st.columns([1, 2])

with col1:
    st.header("⚙️ Điều khiển")
    user_prompt = st.text_input("Nhập yêu cầu cho AI:", "Lập kế hoạch tối ưu hóa bộ nhớ cho World Model.")
    
    # Nút bấm kích hoạt luồng nền
    if st.button("Kích hoạt AI chạy nền", disabled=st.session_state.ai_running):
        st.session_state.ai_running = True
        st.session_state.ai_status = "Đang xử lý..."
        st.session_state.ai_logs = [] # Xóa log cũ
        
        # Tạo một luồng daemon (chạy nền) để không làm treo Streamlit
        ai_thread = threading.Thread(
            target=heavy_ai_task, 
            args=(user_prompt, st.session_state.log_queue),
            daemon=True
        )
        ai_thread.start()
        st.rerun()

    # Nút test độ mượt của UI (Chứng minh UI không bị đơ)
    st.write("---")
    st.subheader("Interactive Test")
    st.write("Bấm nút dưới này lúc AI đang chạy nền để thấy UI vẫn phản hồi mượt mà:")
    if st.button("Bấm tôi để test UI (Click Counter)"):
        st.toast("UI vẫn hoạt động hoàn hảo! ✨")

with col2:
    st.header("🖥️ Nhật ký hoạt động của AI (Real-time Logs)")
    
    # Hiển thị trạng thái hiện tại bằng Badge màu sắc
    if st.session_state.ai_running:
        st.info(f"Trạng thái: {st.session_state.ai_status}")
    else:
        st.success(f"Trạng thái: {st.session_state.ai_status}")

    # Khung hiển thị Log
    log_container = st.empty()
    
    # 5. Vòng lặp kiểm tra hàng đợi (Queue Consumer) để cập nhật UI liên tục
    while st.session_state.ai_running:
        # Lấy tất cả các log mới có trong hàng đợi ra
        while not st.session_state.log_queue.empty():
            log_message = st.session_state.log_queue.get()
            st.session_state.ai_logs.append(log_message)
            
            # Nếu AI báo hoàn thành hoặc lỗi thì dừng trạng thái chạy nền
            if "[KẾT QUẢ]" in log_message or "[LỖI]" in log_message:
                st.session_state.ai_running = False
                st.session_state.ai_status = "Đã hoàn thành"

        # Hiển thị danh sách log ra màn hình
        with log_container.container():
            for log in st.session_state.ai_logs:
                if "[HỆ THỐNG]" in log:
                    st.code(log, language="bash")
                elif "[SUY NGHĨ]" in log:
                    st.warning(log)
                elif "[LẬP KẾ HOẠCH]" in log:
                    st.info(log)
                elif "[KẾT QUẢ]" in log:
                    st.success(log)
                else:
                    st.write(log)
        
        # Chờ một chút trước khi check queue tiếp theo (tránh nghẽn CPU luồng chính)
        time.sleep(0.5)
        
        # Rerun lại nếu AI vừa đổi trạng thái sang False để cập nhật UI lần cuối
        if not st.session_state.ai_running:
            st.rerun()

    # Nếu AI không chạy, chỉ hiển thị lại log cũ đã lưu trong session_state
    if not st.session_state.ai_running and st.session_state.ai_logs:
        with log_container.container():
            for log in st.session_state.ai_logs:
                st.write(log)
