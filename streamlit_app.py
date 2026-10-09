import streamlit as st
import pandas as pd
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Wikifacts Beta | Nền Tảng Dữ Liệu Web",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- QUẢN LÝ DỮ LIỆU BẰNG SESSION STATE ---
if "data_store" not in st.session_state:
    st.session_state.data_store = pd.DataFrame({
        "ID": [101, 102, 103, 104, 105, 106],
        "Tiêu đề bài viết / Nguồn": [
             "Báo cáo xu hướng công nghệ AI toàn cầu Q2/2026",
             "Phân tích thị trường hạ tầng đám mây phi tập trung",
             "Nghiên cứu hành vi tiêu dùng số thế hệ Gen Z",
             "Cập nhật quy định pháp lý về dữ liệu mở châu Âu",
             "Đánh giá hiệu suất các mô hình ngôn ngữ lớn (LLM)",
             "Xu hướng đầu tư Venture Capital vào DeepTech"
        ],
        "Danh mục": ["AI & Data", "Infrastructure", "Market Research", "Legal & Policy", "AI & Data", "Finance"],
        "Nguồn gốc web": ["reuters.com", "techcrunch.com", "bloomberg.com", "euractiv.com", "arxiv.org", "crunchbase.com"],
        "Độ tin cậy": ["99.4%", "98.7%", "97.5%", "99.1%", "99.8%", "96.9%"],
        "Thời gian cập nhật": ["10 phút trước", "1 giờ trước", "3 giờ trước", "5 giờ trước", "1 ngày trước", "2 ngày trước"]
    })

# --- THANH BÊN (SIDEBAR) & MENU ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/internet.png", width=64)
    st.title("Wikifacts Core")
    st.caption("Phiên bản Demo MVP v1.0")
    
    st.divider()
    
    menu = st.radio(
        "Chức năng chính:",
        ["🔍 Tra cứu & Lọc dữ liệu", "⚡ Mô phỏng Quét Web (Live Crawler)", "📊 Báo cáo & Thống kê", "🔒 Quản trị (Admin Panel)"]
    )
    
    st.divider()
    st.markdown("### 🎯 Mục tiêu gọi vốn")
    st.info(
        "**Vòng:** Pre-Seed\n"
        "**Bài toán:** Tự động hóa cấu trúc hóa dữ liệu web bằng công nghệ AI."
    )

df = st.session_state.data_store

# --- GIAO DIỆN CHÍNH ---

if menu == "🔍 Tra cứu & Lọc dữ liệu":
    st.title("🌐 Wikifacts — Công Cụ Tra Cứu Dữ Liệu Thông Minh")
    st.markdown("Trải nghiệm khả năng phân loại, cấu trúc hóa và tìm kiếm thông tin tức thời từ hàng triệu nguồn web.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Tìm kiếm tri thức trong kho lưu trữ:",
            placeholder="Nhập từ khóa (ví dụ: AI, Cloud, Venture Capital...)",
            key="search_input_main"
        )
    with col2:
        selected_category = st.selectbox(
            "Lọc danh mục dữ liệu:",
            ["Tất cả"] + list(df["Danh mục"].unique()),
            key="category_select_main"
        )
        
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["Tiêu đề bài viết / Nguồn"].str.contains(search_query, case=False, na=False) |
            filtered_df["Nguồn gốc web"].str.contains(search_query, case=False, na=False)
        ]
    if selected_category != "Tất cả":
        filtered_df = filtered_df[filtered_df["Danh mục"] == selected_category]
        
    st.markdown("### 📋 Kết quả trích xuất thời gian thực")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng bản ghi hiển thị", f"{len(filtered_df)} kết quả")
    m2.metric("Tốc độ phản hồi trung bình", "0.04 giây")
    m3.metric("Độ chính xác dữ liệu", "98.9%")

elif menu == "⚡ Mô phỏng Quét Web (Live Crawler)":
    st.title("⚡ Mô Phỏng Công Nghệ Quét Web (Live Crawler)")
    st.markdown("Trình diễn năng lực tự động thu thập, làm sạch và chuẩn hóa dữ liệu từ các trang web mục tiêu.")
    
    target_url = st.text_input(
        "Nhập URL trang web cần quét thử nghiệm:", 
        value="https://example-tech-news.com/articles",
        key="crawler_url_input"
    )
    
    if st.button("🚀 Bắt đầu tiến trình quét dữ liệu", type="primary", key="btn_run_crawler"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Đang thiết lập kết nối an toàn với máy chủ đích...")
        time.sleep(0.4)
        progress_bar.progress(30)
        
        status_text.text("Đang bóc tách mã nguồn HTML & loại bỏ nhiễu quảng cáo...")
        time.sleep(0.4)
        progress_bar.progress(70)
        
        status_text.text("Đang cấu trúc hóa dữ liệu bằng mô hình AI...")
        time.sleep(0.4)
        progress_bar.progress(100)
        
        status_text.text("✅ Hoàn thành quét và đồng bộ vào cơ sở dữ liệu thành công!")
        
        st.success("Kết quả trích xuất mẫu từ URL:")
        st.json({
            "url_target": target_url,
            "status_code": 200,
            "extracted_title": "Báo cáo chuyển đổi số và dữ liệu lớn 2026",
            "key_entities": ["Cloud Computing", "AI Automation", "Data Pipeline"],
            "summary": "Nội dung đã được chuẩn hóa tự động vào hệ thống Wikifacts với độ sạch đạt 99.2%."
        })

elif menu == "📊 Báo cáo & Thống kê":
    st.title("📊 Tổng Quan Hệ Thống & Hiệu Năng")
    st.markdown("Số liệu tổng hợp về quy mô dữ liệu và khả năng vận hành của nền tảng.")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng nguồn web index", f"{1240500 + len(df)}+", "Live update")
    c2.metric("Dữ liệu cấu trúc hóa", "45.8 GB", "Live update")
    c3.metric("Độ trễ trung bình", "42 ms", "-5ms tối ưu")
    c4.metric("Hệ thống hoạt động", "99.99%", "Ổn định")
    
    st.divider()
    
    st.subheader("📈 Phân bổ danh mục dữ liệu trong kho lưu trữ")
    category_counts = df["Danh mục"].value_counts().reset_index()
    category_counts.columns = ["Danh mục", "Số lượng"]
    st.bar_chart(category_counts, x="Danh mục", y="Số lượng", color="#1f77b4")

elif menu == "🔒 Quản trị (Admin Panel)":
    st.title("🔒 Khu Vực Quản Trị Hệ Thống (Admin)")
    st.markdown("Đăng nhập quyền quản trị để thêm mới dữ liệu, cấu hình nguồn quét và quản lý kho lưu trữ.")
    
    admin_password = st.text_input(
        "Nhập mật khẩu Admin quản trị:", 
        type="password", 
        placeholder="Mật khẩu...",
        key="admin_pwd_input"
    )
    
    if admin_password == "admin123":
        st.success("🔓 Đăng nhập quyền quản trị thành công!")
        st.divider()
        
        st.subheader("➕ Đăng tải bản ghi dữ liệu mới lên hệ thống")
        
        with st.form("add_data_form_unique"):
            new_title = st.text_input("Tiêu đề bài viết / Báo cáo mới:")
            col_a, col_b = st.columns(2)
            with col_a:
                new_category = st.selectbox(
                    "Chọn danh mục bài viết:", 
                    ["AI & Data", "Infrastructure", "Market Research", "Legal & Policy", "Finance", "DeepTech"],
                    key="form_cat_select"
                )
            with col_b:
                new_source = st.text_input("Nguồn gốc web:", value="wikifacts.internal", key="form_source_input")
                
            submitted = st.form_submit_button("📤 Đăng dữ liệu lên hệ thống Live", type="primary")
            
            if submitted:
                if new_title:
                    new_id = int(df["ID"].max() + 1)
                    new_row = {
                        "ID": new_id,
                        "Tiêu đề bài viết / Nguồn": new_title,
                        "Danh mục": new_category,
                        "Nguồn gốc web": new_source,
                        "Độ tin cậy": "99.5%",
                        "Thời gian cập nhật": "Vừa xong"
                    }
                    st.session_state.data_store = pd.concat([pd.DataFrame([new_row]), st.session_state.data_store], ignore_index=True)
                    st.success(f"🎉 Đã đăng thành công bài viết: '{new_title}' lên hệ thống!")
                    st.balloons()
                else:
                    st.warning("Vui lòng điền tiêu đề bài viết trước khi đăng.")
                    
        st.divider()
        st.subheader("📋 Quản lý toàn bộ kho dữ liệu hệ thống")
        st.dataframe(st.session_state.data_store, use_container_width=True, hide_index=True)
        
    elif admin_password:
        st.error("❌ Mật khẩu không chính xác! (Gợi ý mật khẩu demo: admin123)")
    else:
        st.info("Vui lòng nhập mật khẩu quản trị để tiếp tục. (Mật khẩu demo: `admin123`)")
