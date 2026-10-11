import streamlit as st
import json
from datetime import datetime
import hashlib
import os

# Tự động cấu hình tăng giới hạn upload lên 1GB (1024MB)
os.makedirs(".streamlit", exist_ok=True)
with open(".streamlit/config.toml", "w") as f:
    f.write("[server]\nmaxUploadSize = 1024\n")

st.set_page_config(page_title="Wiki AI & Data", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1 { color: #2c3e50; text-align: center; margin-top: 0px; margin-bottom: 12px; }
    /* Ẩn icon liên kết cạnh tiêu đề */
    h1 a, h2 a, h3 a, .stHeadingWithAction a { display: none !important; }
    .meta { color: #7f8c8d; font-size: 0.9em; }
    div.stFormSubmitButton > button {
        background-color: #0066cc !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "articles" not in st.session_state:
    st.session_state.articles = []

ADMIN_PASSWORD = "admin123"

def make_id(title):
    return hashlib.md5((title + str(datetime.now().timestamp())).encode()).hexdigest()[:10]

# ==================== ĐĂNG NHẬP ====================
if not st.session_state.admin_logged_in:
    col1, col2, col3 = st.columns([1, 1.1, 1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>🔐 Đăng nhập Admin</h1>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Tài khoản", value="admin")
            password = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Đăng nhập", use_container_width=True):
                if username == "admin" and password == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

# ==================== TIÊU ĐỀ + THANH ĐIỀU KHIỂN ====================
st.markdown("<h1 style='text-align:center;'>Wiki về AI và Dữ liệu</h1>", unsafe_allow_html=True)

# Ô chọn bài viết (với placeholder "Tìm kiếm...") và nút menu
_, col_select, col_btn = st.columns([1, 6, 1])

with col_select:
    titles = [a.get("title", "Không tiêu đề") for a in st.session_state.articles]
    selected = st.selectbox(" ", ["Tìm kiếm..."] + titles, label_visibility="collapsed")

with col_btn:
    with st.popover("☰"):
        # Khung tài khoản có viền chữ nhật giống phần tải tệp
        with st.container(border=True):
            st.markdown("**Tài khoản**")
            st.success("Đã đăng nhập (Admin)")
            if st.button("Đăng xuất"):
                st.session_state.admin_logged_in = False
                st.rerun()

        st.markdown("")
        
        # Khung tải tệp có viền chữ nhật
        with st.container(border=True):
            st.markdown("**Tải tệp lên**")
            with st.form("upload_form", clear_on_submit=True):
                ten_muc = st.text_input("Tên mục mới:", max_chars=1000)
                # Bỏ type để không hiển thị danh sách đuôi file, hỗ trợ file lớn (1GB)
                files = st.file_uploader(
                    "Chọn file",
                    accept_multiple_files=True
                )
                if st.form_submit_button("Tải lên"):
                    if files:
                        json_files = [f for f in files if f.name.lower().endswith(".json")]
                        other_files = [f for f in files if not f.name.lower().endswith(".json")]

                        for jf in json_files:
                            try:
                                data = json.load(jf)
                                if isinstance(data, list):
                                    for item in data:
                                        if "id" not in item:
                                            item["id"] = make_id(item.get("title", "item"))
                                    st.session_state.articles = data
                                    st.success("Đã tải JSON")
                            except:
                                st.error("Lỗi JSON")

                        if other_files and ten_muc.strip():
                            payload = []
                            for f in other_files:
                                payload.append({
                                    "file_name": f.name,
                                    "file_type": f.type or "",
                                    "file_data": f.getvalue()
                                })
                            st.session_state.articles.append({
                                "id": make_id(ten_muc),
                                "title": ten_muc.strip(),
                                "source": "Admin",
                                "source_url": "#",
                                "updated": datetime.now().strftime("%Y-%m-%d"),
                                "type": "multi_media",
                                "files_list": payload
                            })
                            st.success(f"Đã tạo: {ten_muc.strip()}")
                        elif other_files:
                            st.warning("Nhập tên mục trước.")
                        st.rerun()

# ==================== NỘI DUNG ====================
if selected == "Tìm kiếm...":
    if st.session_state.articles:
        for a in st.session_state.articles:
            st.markdown(f"**{a.get('title')}**")
            st.caption(f"Cập nhật: {a.get('updated', '')}")
            st.markdown("---")
    else:
        st.caption("Chưa có bài viết nào.")
else:
    art = next((a for a in st.session_state.articles if a.get("title") == selected), None)
    if art:
        st.header(art.get("title"))
        st.caption(f"Cập nhật: {art.get('updated', '')}")
        st.markdown("---")

        if art.get("type") == "multi_media":
            for i, f in enumerate(art.get("files_list", [])):
                st.write(f"**{f.get('file_name')}**")
                data = f.get("file_data")
                if data and f.get("file_type", "").startswith("image/"):
                    st.image(data, width=500)
                if data:
                    st.download_button("Tải xuống", data=data, file_name=f.get("file_name"), key=f"dl{i}")
                st.markdown("---")
        else:
            st.write(art.get("content", ""))

        if art.get("type") != "multi_media":
            st.subheader("Chỉnh sửa")
            with st.form(f"edit_{art.get('id')}"):
                new_title = st.text_input("Tiêu đề", value=art.get("title", ""), max_chars=1000)
                new_content = st.text_area("Nội dung", value=art.get("content", ""), height=200, max_chars=1000)
                if st.form_submit_button("Lưu"):
                    art["title"] = new_title
                    art["content"] = new_content
                    art["updated"] = datetime.now().strftime("%Y-%m-%d")
                    st.success("Đã lưu")
                    st.rerun()
