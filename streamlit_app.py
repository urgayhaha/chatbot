import streamlit as st
import json
from datetime import datetime
import hashlib

st.set_page_config(page_title="Wiki AI & Data", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1 { color: #2c3e50; }
    .meta { color: #7f8c8d; font-size: 0.9em; }
    div.stFormSubmitButton > button {
        background-color: #0066cc !important;
        color: white !important;
    }
    /* Khung menu bên phải */
    .menu-box {
        background: white;
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-top: 8px;
    }
    /* Thu nhỏ ô nhập */
    .stTextInput > div > div > input {
        max-width: 280px;
    }
</style>
""", unsafe_allow_html=True)

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "articles" not in st.session_state:
    st.session_state.articles = []
if "show_menu" not in st.session_state:
    st.session_state.show_menu = False

ADMIN_PASSWORD = "admin123"

def make_id(title):
    return hashlib.md5((title + str(datetime.now().timestamp())).encode()).hexdigest()[:10]

# ==================== ĐĂNG NHẬP (chính giữa) ====================
if not st.session_state.admin_logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.title("🔐 Đăng nhập Admin")
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

# ==================== THANH TRÊN + MENU 3 GẠCH ====================
top_left, top_right = st.columns([8, 1])
with top_left:
    st.title("Wiki về AI và Dữ liệu")
with top_right:
    if st.button("☰", help="Menu", key="menu_btn"):
        st.session_state.show_menu = not st.session_state.show_menu

# Menu hiện bên phải, dưới nút ☰
if st.session_state.show_menu:
    _, menu_col = st.columns([6, 2])
    with menu_col:
        st.markdown('<div class="menu-box">', unsafe_allow_html=True)
        st.markdown("**Tài khoản**")
        st.success("Đã đăng nhập (Admin)")
        if st.button("Đăng xuất", key="logout_btn"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.markdown("---")
        st.markdown("**Tải tệp lên**")
        with st.form("upload_form", clear_on_submit=True):
            ten_muc = st.text_input("Tên mục mới:", key="ten_muc")
            files = st.file_uploader(
                "Chọn file",
                type=["json", "png", "jpg", "jpeg", "pdf", "txt", "docx", "md"],
                accept_multiple_files=True,
                key="file_up"
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
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== NỘI DUNG CHÍNH ====================
titles = [a.get("title", "Không tiêu đề") for a in st.session_state.articles]
selected = st.selectbox("Chọn chủ đề:", ["-- Chọn bài viết --"] + titles)

if selected == "-- Chọn bài viết --":
    st.info("Chọn một chủ đề để xem.")
    for a in st.session_state.articles:
        st.markdown(f"**{a.get('title')}**")
        st.caption(f"Cập nhật: {a.get('updated', '')}")
        st.markdown("---")
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
                new_title = st.text_input("Tiêu đề", value=art.get("title", ""))
                new_content = st.text_area("Nội dung", value=art.get("content", ""), height=200)
                if st.form_submit_button("Lưu"):
                    art["title"] = new_title
                    art["content"] = new_content
                    art["updated"] = datetime.now().strftime("%Y-%m-%d")
                    st.success("Đã lưu")
                    st.rerun()

st.caption("Dữ liệu chỉ tồn tại trong phiên làm việc hiện tại.")
