import streamlit as st
import json
from datetime import datetime
import hashlib

# Page config
st.set_page_config(
    page_title="Wiki AI & Data",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
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

# Hàm tạo id an toàn nếu thiếu
def ensure_id(article):
    if "id" not in article or not article["id"]:
        title = article.get("title", "untitled")
        article["id"] = hashlib.md5(title.encode()).hexdigest()[:12]
    return article

# Dữ liệu mặc định
DEFAULT_ARTICLES = [
    {
        "id": "ai",
        "title": "Artificial Intelligence (AI)",
        "content": """Artificial intelligence (AI) is the capability of computational systems to perform tasks typically associated with human intelligence, such as learning, reasoning, problem-solving, perception, and decision-making. It is a field of research in engineering, mathematics, and computer science that develops and studies methods and software enabling machines to perceive their environment and use learning and intelligence to take actions that maximize their chances of achieving defined goals.

High-profile applications of AI include advanced web search engines, chatbots, virtual assistants, autonomous vehicles, play and analysis in strategy games (e.g., chess and Go), and content generation (e.g., text, images, audio, and videos).

Artificial intelligence was founded as an academic discipline in 1956. The field experienced multiple cycles of optimism followed by periods of disappointment and loss of funding, known as AI winters. Funding and interest increased substantially after 2012, with the use of graphics processing units (GPUs) to accelerate neural networks and deep learning.""",
        "source": "Wikipedia - Artificial intelligence",
        "source_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "updated": "2026-10-10",
        "type": "article"
    },
    {
        "id": "ml",
        "title": "Machine Learning (ML)",
        "content": """Machine learning (ML) is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data, and thus perform tasks without being explicitly programmed.

Key paradigms include supervised learning, unsupervised learning, and reinforcement learning. The term "machine learning" was coined in 1959 by Arthur Samuel. Advances in deep learning have made ML central to modern AI applications.""",
        "source": "Wikipedia - Machine learning",
        "source_url": "https://en.wikipedia.org/wiki/Machine_learning",
        "updated": "2026-10-10",
        "type": "article"
    },
    {
        "id": "dl",
        "title": "Deep Learning (DL)",
        "content": """Deep learning (DL) focuses on utilizing multilayered neural networks to perform tasks such as classification, regression, and representation learning. It takes inspiration from biological neuroscience and involves stacking artificial neurons into layers.

Deep learning is a subfield of machine learning that uses neural networks with many layers to model complex patterns in data. It has driven major advances in image recognition, speech processing, and generative AI.""",
        "source": "Wikipedia - Deep learning",
        "source_url": "https://en.wikipedia.org/wiki/Deep_learning",
        "updated": "2026-10-10",
        "type": "article"
    },
    {
        "id": "nn",
        "title": "Artificial Neural Networks (ANN)",
        "content": """An artificial neural network (ANN) is a computational model inspired by biological neural networks, consisting of interconnected artificial neurons organized in layers. Each neuron processes signals via weights and activation functions.

ANNs form the core of deep learning and excel in tasks like image recognition, speech processing, and natural language tasks.""",
        "source": "Wikipedia - Artificial neural network",
        "source_url": "https://en.wikipedia.org/wiki/Artificial_neural_network",
        "updated": "2026-10-10",
        "type": "article"
    },
    {
        "id": "bigdata",
        "title": "Big Data",
        "content": """Big data refers to data sets that are too large or complex to be dealt with by traditional data-processing software. It is characterized by the three V's: volume, velocity, and variety.

Big data analysis uses predictive analytics and machine learning to extract value in fields like healthcare, business, and science.""",
        "source": "Wikipedia - Big data",
        "source_url": "https://en.wikipedia.org/wiki/Big_data",
        "updated": "2026-10-10",
        "type": "article"
    },
    {
        "id": "datascience",
        "title": "Data Science",
        "content": """Data science is an interdisciplinary field that uses statistics, scientific computing, algorithms, and coding to extract knowledge from structured or unstructured data.

A data scientist combines programming and statistical knowledge to extract actionable insights from data.""",
        "source": "Wikipedia - Data science",
        "source_url": "https://en.wikipedia.org/wiki/Data_science",
        "updated": "2026-10-10",
        "type": "article"
    }
]

# Session state
if "articles" not in st.session_state:
    st.session_state.articles = [ensure_id(a) for a in DEFAULT_ARTICLES.copy()]

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

ADMIN_PASSWORD = "admin123"

# Sidebar
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
                st.success("Đăng nhập thành công!")
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
        
        # Backup JSON
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
        st.download_button(
            label="Tải dữ liệu bài viết (JSON)",
            data=data_json,
            file_name="wiki_data.json",
            mime="application/json"
        )
        
        st.markdown("---")
        st.markdown('<p class="upload-label">Tải tệp lên - Upload</p>', unsafe_allow_html=True)
        
        with st.form("upload_combined_form", clear_on_submit=True):
            custom_topic_name = st.text_input("Nhập tên mục / chủ đề mới:")
            
            uploaded_files = st.file_uploader(
                "Chọn file (JSON để khôi phục dữ liệu, hoặc hình/tài liệu để tạo mục mới)",
                type=["json", "png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "docx", "doc", "md", "csv"],
                accept_multiple_files=True
            )
            
            upload_submitted = st.form_submit_button("Tải lên")
            
            if upload_submitted and uploaded_files:
                json_files = [f for f in uploaded_files if f.name.lower().endswith(".json")]
                other_files = [f for f in uploaded_files if not f.name.lower().endswith(".json")]
                
                # Xử lý JSON
                if json_files:
                    for jf in json_files:
                        try:
                            new_data = json.load(jf)
                            if isinstance(new_data, list):
                                # Đảm bảo mọi bài đều có id
                                st.session_state.articles = [ensure_id(a) for a in new_data]
                                st.success("Đã khôi phục dữ liệu từ JSON!")
                            else:
                                st.warning(f"File {jf.name} không đúng định dạng.")
                        except Exception as e:
                            st.error(f"Lỗi đọc JSON {jf.name}: {e}")
                
                # Xử lý file media
                if other_files:
                    if not custom_topic_name.strip():
                        st.warning("Vui lòng nhập tên mục khi tải lên hình hoặc tài liệu.")
                    elif len(other_files) > 10:
                        st.warning("Chỉ được tải tối đa 10 tệp trong một lần!")
                    else:
                        files_payload = []
                        for uploaded_file in other_files:
                            file_bytes = uploaded_file.getvalue()
                            file_type = uploaded_file.type or ""
                            
                            file_text_content = ""
                            if uploaded_file.name.lower().endswith(('.txt', '.md', '.csv')):
                                try:
                                    file_text_content = file_bytes.decode('utf-8', errors='ignore')
                                except:
                                    pass
                            
                            files_payload.append({
                                "file_name": uploaded_file.name,
                                "file_type": file_type,
                                "file_data": file_bytes,
                                "text_content": file_text_content
                            })
                        
                        new_media_article = ensure_id({
                            "title": custom_topic_name.strip(),
                            "source": "Tải lên bởi Admin",
                            "source_url": "#",
                            "updated": datetime.now().strftime("%Y-%m-%d"),
                            "type": "multi_media",
                            "files_list": files_payload
                        })
                        st.session_state.articles.append(new_media_article)
                        st.success(f"Đã tạo mục '{custom_topic_name}' với {len(other_files)} tệp!")
                
                if json_files or other_files:
                    st.rerun()

# Main content
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
        elif art.get("type") == "media":
            badge = "[Tệp/Tài liệu]"
            
        st.markdown(f"**{art.get('title', 'Không tiêu đề')}** {badge}")
        st.markdown(f"<span class='meta'>Cập nhật: {art.get('updated', '')} | Nguồn: {art.get('source', '')}</span>", unsafe_allow_html=True)
        st.markdown("---")
else:
    article = next((ensure_id(a) for a in st.session_state.articles if a.get("title") == selected_title), None)
    if article:
        st.header(article.get("title", "Không tiêu đề"))
        st.markdown(f"<span class='meta'>Cập nhật lần cuối: **{article.get('updated', '')}**</span>", unsafe_allow_html=True)
        source_url = article.get("source_url", "#")
        st.markdown(f"<span class='meta'>Nguồn: [{article.get('source', 'Không rõ')}]({source_url})</span>", unsafe_allow_html=True)
        st.markdown("---")
        
        if article.get("type") == "multi_media":
            files_list = article.get("files_list", [])
            st.info(f"Mục này chứa tổng cộng {len(files_list)} tệp đính kèm.")
            
            for idx, file_item in enumerate(files_list):
                st.markdown(f"### Tệp {idx + 1}: `{file_item.get('file_name', 'file')}`")
                f_data = file_item.get("file_data")
                f_type = file_item.get("file_type", "")
                
                if f_data and f_type and f_type.startswith("image/"):
                    st.image(f_data, width=600)
                else:
                    if file_item.get("text_content"):
                        st.text_area(
                            f"Nội dung văn bản ({file_item.get('file_name')})",
                            value=file_item["text_content"],
                            height=200,
                            disabled=True,
                            key=f"txt_area_{article['id']}_{idx}"
                        )
                
                if f_data:
                    st.download_button(
                        label=f"Tải xuống {file_item.get('file_name', 'file')}",
                        data=f_data,
                        file_name=file_item.get('file_name', 'file'),
                        mime=f_type or "application/octet-stream",
                        key=f"dl_multi_{article['id']}_{idx}"
                    )
                st.markdown("---")
        else:
            st.markdown(article.get("content", "Không có nội dung."))
        
        # Admin actions
        if st.session_state.admin_logged_in:
            st.markdown("---")
            if article.get("type") not in ["media", "multi_media"]:
                st.subheader("Chỉnh sửa bài viết (Admin)")
                with st.form(key=f"edit_{article['id']}"):
                    new_title = st.text_input("Tiêu đề", value=article.get("title", ""))
                    new_content = st.text_area("Nội dung", value=article.get("content", ""), height=300)
                    new_source = st.text_input("Tên nguồn", value=article.get("source", ""))
                    new_url = st.text_input("URL nguồn", value=article.get("source_url", ""))
                    new_updated = st.text_input("Ngày cập nhật (YYYY-MM-DD)", value=article.get("updated", ""))
                    
                    if st.form_submit_button("Lưu thay đổi"):
                        article["title"] = new_title
                        article["content"] = new_content
                        article["source"] = new_source
                        article["source_url"] = new_url
                        article["updated"] = new_updated or datetime.now().strftime("%Y-%m-%d")
                        st.success("Đã lưu thay đổi!")
                        st.rerun()
            
            if st.button("Xóa mục này khỏi hệ thống", key=f"delete_article_{article['id']}"):
                st.session_state.articles = [a for a in st.session_state.articles if a.get("id") != article["id"]]
                st.success("Đã xóa mục thành công!")
                st.rerun()
                
            if article.get("type") not in ["media", "multi_media"]:
                st.markdown("---")
                st.subheader("Thêm bài viết mới")
                with st.form(key="add_new"):
                    add_title = st.text_input("Tiêu đề mới")
                    add_content = st.text_area("Nội dung mới", height=200)
                    add_source = st.text_input("Nguồn", value="Wikipedia")
                    add_url = st.text_input("URL nguồn")
                    if st.form_submit_button("Thêm bài viết"):
                        if add_title and add_content:
                            new_article = ensure_id({
                                "title": add_title,
                                "content": add_content,
                                "source": add_source,
                                "source_url": add_url or "#",
                                "updated": datetime.now().strftime("%Y-%m-%d"),
                                "type": "article"
                            })
                            st.session_state.articles.append(new_article)
                            st.success("Đã thêm bài viết!")
                            st.rerun()
                        else:
                            st.warning("Cần tiêu đề và nội dung.")
    else:
        st.error("Không tìm thấy bài viết.")

st.markdown("---")
st.caption("Ứng dụng Wiki đơn giản chạy trên Streamlit. Dữ liệu và file tải lên chỉ lưu trong phiên hiện tại.")
