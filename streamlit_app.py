import streamlit as st
import json
from datetime import datetime
import hashlib

st.set_page_config(
    page_title="Wiki AI & Data",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1 { color: #2c3e50; font-weight: 500; }
    h2 { color: #34495e; }
    .meta { color: #7f8c8d; font-size: 0.9em; }
    div.stButton > button:first-child,
    div.stFormSubmitButton > button {
        background-color: #0066cc !important;
        color: white !important;
        border-radius: 6px;
        border: none;
        font-weight: 600;
        width: 100%;
    }
    div.stButton > button:first-child:hover,
    div.stFormSubmitButton > button:hover {
        background-color: #004d99 !important;
        color: white !important;
    }
    .upload-label {
        color: #0066cc;
        font-weight: 600;
        font-size: 1.05em;
    }
</style>
""", unsafe_allow_html=True)

def ensure_id(article):
    if not article.get("id"):
        title = article.get("title", "untitled")
        article["id"] = hashlib.md5((title + str(datetime.now().timestamp())).encode()).hexdigest()[:12]
    return article

DEFAULT_ARTICLES = [
    {"id": "ai", "title": "Artificial Intelligence (AI)", "content": "Artificial intelligence (AI) is the capability of computational systems to perform tasks typically associated with human intelligence...", "source": "Wikipedia", "source_url": "https://en.wikipedia.org/wiki/Artificial_intelligence", "updated": "2026-10-10", "type": "article"},
    {"id": "ml", "title": "Machine Learning (ML)", "content": "Machine learning (ML) is a field of study in artificial intelligence...", "source": "Wikipedia", "source_url": "https://en.wikipedia.org/wiki/Machine_learning", "updated": "2026-10-10", "type": "article"},
    {"id": "dl", "title": "Deep Learning (DL)", "content": "Deep learning (DL) focuses on utilizing multilayered neural networks...", "source": "Wikipedia", "source_url": "https://en.wikipedia.org/wiki/Deep_learning", "updated": "2026-10-10", "type": "article"},
    {"id": "nn", "title": "Artificial Neural Networks (ANN)", "content": "An artificial neural network (ANN) is a computational model...", "source": "Wikipedia", "source_url": "https://en.wikipedia.org/wiki/Artificial_neural_network", "updated": "2026-10-10", "type": "article"},
    {"id": "bigdata", "title": "Big Data", "content": "Big data refers to data sets that are too large or complex...", "source": "Wikipedia", "source_url": "https://en.wikipedia.org/wiki/Big_data", "updated": "2026-10-10", "type": "article"},
    {"id": "datascience", "title": "Data Science", "content": "Data science is an interdisciplinary field...", "source": "Wikipedia", "source_url": "https://en.wikipedia.org/wiki/Data_science", "updated": "2026-10-10", "type": "article"}
]

if "articles" not in st.session_state:
    st.session_state.articles = [ensure_id(a) for a in DEFAULT_ARTICLES]

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

ADMIN_PASSWORD = "admin123"

with st.sidebar:
    st.title("Wiki AI & Data")
    st.markdown("---")
    
    titles = [art.get("title", "Không tiêu đề") for art in st.session_state.articles]
    selected_title = st.selectbox("Chọn chủ đề:", ["-- Chọn bài viết --"] + titles)
    
    st.markdown("---")
    st.subheader("Admin")
    
    if not st.session_state.admin_logged_in:
        password = st.text_input("Mật khẩu admin:", type="password")
        if st.button("Đăng nhập"):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Sai mật khẩu!")
    else:
        st.success("Đã đăng nhập (Admin)")
        if st.button("Đăng xuất"):
            st.session_state.admin_logged_in = False
            st.rerun()
        
        st.markdown("---")
        st.subheader("Quản lý Dữ liệu & Tệp")
        
        export_articles = []
        for art in st.session_state.articles:
            art_copy = art.copy()
            if "files_list" in art_copy:
                clean_files = []
                for f in art_copy["files_list"]:
                    f_c = f.copy()
                    f_c["file_data"] = "[binary]"
                    clean_files.append(f_c)
                art_copy["files_list"] = clean_files
            export_articles.append(art_copy)
        
        data_json = json.dumps(export_articles, ensure_ascii=False, indent=2)
        st.download_button("Tải dữ liệu bài viết (JSON)", data=data_json, file_name="wiki_data.json", mime="application/json")
        
        st.markdown("---")
        st.markdown('<p class="upload-label">Tải tệp lên - Upload</p>', unsafe_allow_html=True)
        
        with st.form("upload_combined_form", clear_on_submit=True):
            custom_topic_name = st.text_input("Nhập tên mục / chủ đề mới:", key="custom_name_input")
            
            uploaded_files = st.file_uploader(
                "Chọn file (JSON để khôi phục dữ liệu, hoặc hình/tài liệu để tạo mục mới)",
                type=["json", "png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "docx", "doc", "md", "csv"],
                accept_multiple_files=True
            )
            
            upload_submitted = st.form_submit_button("Tải lên")
            
            if upload_submitted and uploaded_files:
                json_files = [f for f in uploaded_files if f.name.lower().endswith(".json")]
                other_files = [f for f in uploaded_files if not f.name.lower().endswith(".json")]
                
                if json_files:
                    for jf in json_files:
                        try:
                            new_data = json.load(jf)
                            if isinstance(new_data, list):
                                st.session_state.articles = [ensure_id(a) for a in new_data]
                                st.success("Đã khôi phục dữ liệu từ JSON!")
                        except Exception as e:
                            st.error(f"Lỗi đọc JSON: {e}")
                
                if other_files:
                    ten_muc = custom_topic_name.strip() if custom_topic_name else ""
                    if not ten_muc:
                        st.warning("Vui lòng nhập tên mục.")
                    elif len(other_files) > 10:
                        st.warning("Tối đa 10 tệp.")
                    else:
                        files_payload = []
                        for uploaded_file in other_files:
                            file_bytes = uploaded_file.getvalue()
                            files_payload.append({
                                "file_name": uploaded_file.name,
                                "file_type": uploaded_file.type or "",
                                "file_data": file_bytes,
                                "text_content": file_bytes.decode('utf-8', errors='ignore') if uploaded_file.name.lower().endswith(('.txt', '.md', '.csv')) else ""
                            })
                        
                        # Giữ nguyên tên người dùng nhập
                        new_media_article = ensure_id({
                            "title": ten_muc,  # Không bị đổi
                            "source": "Tải lên bởi Admin",
                            "source_url": "#",
                            "updated": datetime.now().strftime("%Y-%m-%d"),
                            "type": "multi_media",
                            "files_list": files_payload
                        })
                        st.session_state.articles.append(new_media_article)
                        st.success(f"Đã tạo mục '{ten_muc}' thành công!")
                
                if json_files or other_files:
                    st.rerun()

st.title("Wiki về AI và Dữ liệu")
st.caption("Nguồn nội dung chủ yếu từ Wikipedia. Bố cục đơn giản, dễ đọc.")

if selected_title == "-- Chọn bài viết --":
    st.info("Hãy chọn một chủ đề từ thanh bên để xem thông tin.")
    st.markdown("### Các chủ đề hiện có:")
    for art in st.session_state.articles:
        art = ensure_id(art)
        badge = "[Bài viết]"
        if art.get("type") == "multi_media":
            badge = f"[Đa tệp: {len(art.get('files_list', []))}]"
        st.markdown(f"**{art.get('title', 'Không tiêu đề')}** {badge}")
        st.markdown(f"<span class='meta'>Cập nhật: {art.get('updated', '')} | Nguồn: {art.get('source', '')}</span>", unsafe_allow_html=True)
        st.markdown("---")
else:
    article = next((ensure_id(a) for a in st.session_state.articles if a.get("title") == selected_title), None)
    if article:
        st.header(article.get("title", ""))
        st.markdown(f"<span class='meta'>Cập nhật lần cuối: **{article.get('updated', '')}**</span>", unsafe_allow_html=True)
        st.markdown(f"<span class='meta'>Nguồn: [{article.get('source', '')}]({article.get('source_url', '#')})</span>", unsafe_allow_html=True)
        st.markdown("---")
        
        if article.get("type") == "multi_media":
            files_list = article.get("files_list", [])
            st.info(f"Mục này chứa {len(files_list)} tệp.")
            for idx, file_item in enumerate(files_list):
                st.markdown(f"### Tệp {idx+1}: `{file_item.get('file_name')}`")
                f_data = file_item.get("file_data")
                f_type = file_item.get("file_type", "")
                if f_data and f_type.startswith("image/"):
                    st.image(f_data, width=600)
                elif file_item.get("text_content"):
                    st.text_area("Nội dung", value=file_item["text_content"], height=200, disabled=True, key=f"ta_{article['id']}_{idx}")
                if f_data:
                    st.download_button("Tải xuống", data=f_data, file_name=file_item.get("file_name"), key=f"dl_{article['id']}_{idx}")
                st.markdown("---")
        else:
            st.markdown(article.get("content", ""))
        
        if st.session_state.admin_logged_in:
            st.markdown("---")
            if article.get("type") not in ["media", "multi_media"]:
                st.subheader("Chỉnh sửa bài viết (Admin)")
                with st.form(key=f"edit_{article['id']}"):
                    new_title = st.text_input("Tiêu đề", value=article.get("title", ""))
                    new_content = st.text_area("Nội dung", value=article.get("content", ""), height=300)
                    new_source = st.text_input("Nguồn", value=article.get("source", ""))
                    new_url = st.text_input("URL nguồn", value=article.get("source_url", ""))
                    new_updated = st.text_input("Ngày cập nhật", value=article.get("updated", ""))
                    if st.form_submit_button("Lưu thay đổi"):
                        article["title"] = new_title
                        article["content"] = new_content
                        article["source"] = new_source
                        article["source_url"] = new_url
                        article["updated"] = new_updated or datetime.now().strftime("%Y-%m-%d")
                        st.success("Đã lưu!")
                        st.rerun()
            
            if st.button("Xóa mục này", key=f"del_{article['id']}"):
                st.session_state.articles = [a for a in st.session_state.articles if a.get("id") != article["id"]]
                st.rerun()

st.markdown("---")
st.caption("Ứng dụng Wiki đơn giản chạy trên Streamlit.")
