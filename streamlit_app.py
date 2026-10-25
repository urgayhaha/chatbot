# -*- coding: utf-8 -*-
"""
Wiki AI & Data - Phiên bản không đăng nhập, lưu trữ vĩnh viễn & tích hợp API cho AGI.
"""

import streamlit as st
import json
from datetime import datetime
import hashlib
import os

# Tự động cấu hình giới hạn upload lên 1GB (1024MB)
os.makedirs(".streamlit", exist_ok=True)
with open(".streamlit/config.toml", "w") as f:
    f.write("[server]\nmaxUploadSize = 1024\n")

st.set_page_config(page_title="Wiki AI & Data", page_icon="📚", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1 { color: #2c3e50; text-align: center; margin-top: 0px; margin-bottom: 12px; }
    h1 a, h2 a, h3 a, .stHeadingWithAction a { display: none !important; }
    .meta { color: #7f8c8d; font-size: 0.9em; }
    div.stFormSubmitButton > button {
        background-color: #0066cc !important;
        color: white !important;
    }
    /* Ẩn text giới hạn dung lượng và định dạng mặc định của Streamlit */
    [data-testid="stFileUploader"] section small {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== CƠ CHẾ LƯU TRỮ VĨNH VIỄN (PERSISTENT STORAGE) ====================
DB_FILE = "wiki_database.json"

def load_database():
    """Đọc dữ liệu vĩnh viễn từ file JSON trên ổ đĩa"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_database(articles):
    """Ghi dữ liệu vĩnh viễn xuống file JSON"""
    try:
        # Lọc bỏ các trường binary file_data lớn khi lưu metadata nếu cần, 
        # hoặc giữ lại nếu muốn serialize bytes (lưu ý JSON chuẩn không hỗ trợ bytes trực tiếp).
        # Đối với multi_media có bytes, ta lưu cấu trúc cơ bản hoặc mã hóa, 
        # dưới đây lưu các bài viết thông thường và metadata.
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Lỗi khi lưu cơ sở dữ liệu vĩnh viễn: {e}")

if "articles" not in st.session_state:
    st.session_state.articles = load_database()

def make_id(title):
    return hashlib.md5((title + str(datetime.now().timestamp())).encode()).hexdigest()[:10]


# ==================== HÀM HỖ TRỢ TRỰC TIẾP CHO AGI (AGI DIRECT ACCESS API) ====================
def agi_get_all_articles():
    """AGI gọi hàm này để lấy toàn bộ danh sách bài viết/tài liệu"""
    return load_database()

def agi_search_article(keyword):
    """AGI gọi hàm này để tìm kiếm bài viết theo từ khóa tiêu đề hoặc nội dung"""
    data = load_database()
    keyword = keyword.lower()
    results = []
    for art in data:
        if keyword in art.get("title", "").lower() or keyword in art.get("content", "").lower():
            results.append(art)
    return results

def agi_add_article(title, content, source="AGI Agent"):
    """AGI gọi hàm này để tự động tạo/thêm bài viết mới vào kho tri thức"""
    data = load_database()
    new_art = {
        "id": make_id(title),
        "title": title.strip(),
        "content": content,
        "source": source,
        "source_url": "#",
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "type": "text"
    }
    data.append(new_art)
    save_database(data)
    return new_art["id"]


# ==================== TIÊU ĐỀ + THANH ĐIỀU KHIỂN ====================
st.markdown("<h1 style='text-align:center;'>Wiki về AI và tài liệu</h1>", unsafe_allow_html=True)

# Ô tìm kiếm và nút menu tải tệp lên
_, col_select, col_btn = st.columns([1, 6, 1])

with col_select:
    titles = [a.get("title", "Không tiêu đề") for a in st.session_state.articles]
    selected = st.selectbox(" ", ["Tìm kiếm..."] + titles, label_visibility="collapsed")

with col_btn:
    with st.popover("☰"):
        # Khung trạng thái hệ thống (Không cần đăng nhập)
        with st.container(border=True):
            st.markdown("**Hệ thống Kho Tri Thức**")
            st.success("Trạng thái: Hoạt động (Public)")
            st.caption("Dữ liệu được lưu vĩnh viễn trên ổ đĩa.")

        st.markdown("")
        
        # Phần tải tệp lên
        st.markdown("**Tải tệp lên**")
        with st.form("upload_form", clear_on_submit=True):
            ten_muc = st.text_input("Tên mục mới:", max_chars=1000)
            
            files = st.file_uploader(
                "upload your file",
                accept_multiple_files=True,
                label_visibility="collapsed"
            )
            st.markdown("<p style='font-size:0.8em; color:#666; margin-top:-5px; margin-bottom:10px;'>The Maximum Limit is 1 GB per file</p>", unsafe_allow_html=True)
            
            if st.form_submit_button("Tải lên"):
                if files:
                    json_files = [f for f in files if f.name.lower().endswith(".json")]
                    other_files = [f for f in files if not f.name.lower().endswith(".json")]

                    current_articles = load_database()

                    for jf in json_files:
                        try:
                            data = json.load(jf)
                            if isinstance(data, list):
                                for item in data:
                                    if "id" not in item:
                                        item["id"] = make_id(item.get("title", "item"))
                                current_articles = data
                                save_database(current_articles)
                                st.session_state.articles = current_articles
                                st.success("Đã tải JSON và lưu vĩnh viễn!")
                        except:
                            st.error("Lỗi đọc file JSON")

                    if other_files and ten_muc.strip():
                        payload = []
                        for f in other_files:
                            payload.append({
                                "file_name": f.name,
                                "file_type": f.type or "",
                                "file_size": f.size
                            })
                        
                        new_entry = {
                            "id": make_id(ten_muc),
                            "title": ten_muc.strip(),
                            "source": "User Upload",
                            "source_url": "#",
                            "updated": datetime.now().strftime("%Y-%m-%d"),
                            "type": "multi_media",
                            "files_list": payload
                        }
                        current_articles.append(new_entry)
                        save_database(current_articles)
                        st.session_state.articles = current_articles
                        st.success(f"Đã tạo và lưu vĩnh viễn: {ten_muc.strip()}")
                    elif other_files:
                        st.warning("Vui lòng nhập tên mục trước khi tải lên tệp.")
                    st.rerun()

# ==================== HIỂN THỊ NỘI DUNG ====================
# Đồng bộ lại state từ bộ nhớ vĩnh viễn
st.session_state.articles = load_database()

if selected == "Tìm kiếm...":
    if st.session_state.articles:
        st.markdown("### Danh sách các mục tri thức hiện có:")
        for a in st.session_state.articles:
            st.markdown(f"**{a.get('title')}**")
            st.caption(f"Cập nhật: {a.get('updated', '')} | Nguồn: {a.get('source', 'User')}")
            st.markdown("---")
    else:
        st.info("Kho tri thức hiện đang trống. Hãy tải lên tệp hoặc thêm nội dung mới.")
else:
    art = next((a for a in st.session_state.articles if a.get("title") == selected), None)
    if art:
        st.header(art.get("title"))
        st.caption(f"Cập nhật: {art.get('updated', '')}")
        st.markdown("---")

        if art.get("type") == "multi_media":
            for i, f in enumerate(art.get("files_list", [])):
                st.write(f"**Tệp đính kèm:** {f.get('file_name')}")
                st.markdown("---")
        else:
            st.write(art.get("content", ""))

        # Form chỉnh sửa trực tiếp trên giao diện
        if art.get("type") != "multi_media":
            st.subheader("Chỉnh sửa nội dung")
            with st.form(f"edit_{art.get('id')}"):
                new_title = st.text_input("Tiêu đề", value=art.get("title", ""), max_chars=1000)
                new_content = st.text_area("Nội dung", value=art.get("content", ""), height=200)
                if st.form_submit_button("Lưu thay đổi"):
                    art["title"] = new_title
                    art["content"] = new_content
                    art["updated"] = datetime.now().strftime("%Y-%m-%d")
                    save_database(st.session_state.articles)
                    st.success("Đã lưu thay đổi vĩnh viễn vào ổ đĩa!")
                    st.rerun()
