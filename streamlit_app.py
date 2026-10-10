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
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

def make_id(title):
    return hashlib.md5((title + str(datetime.now().timestamp())).encode()).hexdigest()[:10]

if "articles" not in st.session_state:
    st.session_state.articles = []

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

ADMIN_PASSWORD = "admin123"

with st.sidebar:
    st.title("Wiki AI & Data")
    st.markdown("---")

    titles = [a.get("title", "Không tiêu đề") for a in st.session_state.articles]
    selected = st.selectbox("Chọn chủ đề:", ["-- Chọn bài viết --"] + titles)

    st.markdown("---")
    st.subheader("Admin")

    if not st.session_state.admin_logged_in:
        pw = st.text_input("Mật khẩu admin:", type="password")
        if st.button("Đăng nhập") and pw == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
    else:
        st.success("Đã đăng nhập (Admin)")
        if st.button("Đăng xuất"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.markdown("---")
        st.subheader("Tải tệp lên - Upload")

        with st.form("upload_form", clear_on_submit=True):
            ten_muc = st.text_input("Nhập tên mục / chủ đề mới:")
            files = st.file_uploader(
                "Chọn file",
                type=["json", "png", "jpg", "jpeg", "pdf", "txt", "docx", "md"],
                accept_multiple_files=True
            )
            submitted = st.form_submit_button("Tải lên")

            if submitted and files:
                json_files = [f for f in files if f.name.lower().endswith(".json")]
                other_files = [f for f in files if not f.name.lower().endswith(".json")]

                # JSON
                for jf in json_files:
                    try:
                        data = json.load(jf)
                        if isinstance(data, list):
                            for item in data:
                                if "id" not in item:
                                    item["id"] = make_id(item.get("title", "item"))
                            st.session_state.articles = data
                            st.success("Đã tải JSON thành công")
                    except:
                        st.error("Lỗi đọc JSON")

                # File thường
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
                        "title": ten_muc.strip(),   # Giữ nguyên tên người dùng nhập
                        "source": "Admin",
                        "source_url": "#",
                        "updated": datetime.now().strftime("%Y-%m-%d"),
                        "type": "multi_media",
                        "files_list": payload
                    })
                    st.success(f"Đã tạo mục: {ten_muc.strip()}")
                elif other_files:
                    st.warning("Bạn phải nhập tên mục trước khi tải file.")

                st.rerun()

# Nội dung chính
st.title("Wiki về AI và Dữ liệu")

if selected == "-- Chọn bài viết --":
    st.info("Chọn một chủ đề ở bên trái.")
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

        if st.session_state.admin_logged_in and art.get("type") != "multi_media":
            st.subheader("Chỉnh sửa")
            with st.form(f"edit_{art.get('id')}"):
                new_title = st.text_input("Tiêu đề", value=art.get("title", ""))
                new_content = st.text_area("Nội dung", value=art.get("content", ""), height=250)
                if st.form_submit_button("Lưu"):
                    art["title"] = new_title
                    art["content"] = new_content
                    art["updated"] = datetime.now().strftime("%Y-%m-%d")
                    st.success("Đã lưu")
                    st.rerun()

st.caption("Dữ liệu chỉ tồn tại trong phiên làm việc hiện tại.")
