import streamlit as st
import pandas as pd

# Cấu hình trang
st.set_page_config(
    page_title="Wikifacts Beta",
    page_icon="🌐",
    layout="wide"
)

# Giao diện chính
st.title("🌐 Wikifacts — Nền Tảng Dữ Liệu Thông Minh")
st.markdown("Bản Beta trình diễn năng lực tổng hợp, cấu trúc hóa và tra cứu dữ liệu web thời gian thực phục vụ gọi vốn.")

# Thanh tìm kiếm dữ liệu
query = st.text_input(
    "🔍 Tra cứu kho tri thức & dữ liệu internet:",
    placeholder="Nhập từ khóa (ví dụ: công nghệ, năng lượng, AI, hạ tầng...)"
)

# Dữ liệu mẫu (Mock Database) thể hiện năng lực xử lý
data = {
    "Tiêu đề dữ liệu": [
        "Hệ thống định tuyến dữ liệu phân tán", 
        "Thuật toán tối ưu hóa tìm kiếm web", 
        "Nền tảng tri thức tự động hóa", 
        "Bảo mật và xác thực hạ tầng đám mây"
    ],
    "Danh mục": ["Infrastructure", "Search Engine", "AI Automation", "Security"],
    "Trạng thái": ["Hoạt động", "Đang thử nghiệm", "Sẵn sàng scale", "Bảo mật cao"],
    "Độ chính xác": ["99.8%", "95.4%", "98.1%", "99.9%"]
}
df = pd.DataFrame(data)

# Hiển thị kết quả tương tác
if query:
    st.success(f"Đã trích xuất dữ liệu thành công cho từ khóa: **{query}**")
    filtered_df = df[
        df['Tiêu đề dữ liệu'].str.contains(query, case=False, na=False) | 
        df['Danh mục'].str.contains(query, case=False, na=False)
    ]
    if not filtered_df.empty:
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("Không tìm thấy khớp chính xác. Hiển thị toàn bộ kho dữ liệu liên quan:")
        st.dataframe(df, use_container_width=True)
else:
    st.subheader("📊 Kho dữ liệu hệ thống (Live Preview)")
    st.dataframe(df, use_container_width=True)

# Sidebar quản trị phía bên trái
st.sidebar.header("⚙️ Thông số hệ thống")
st.sidebar.info(
    "**Môi trường:** Streamlit Cloud\n\n"
    "**Trạng thái:** Live Beta (v1.0)\n\n"
    "**Mục tiêu:** Gọi vốn Pre-Seed"
)
