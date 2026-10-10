import streamlit as st
import json
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Wiki AI & Data",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS đơn giản
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1 { color: #2c3e50; font-weight: 500; }
    h2 { color: #34495e; }
    .meta { color: #7f8c8d; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

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

# Khởi tạo session state
if "articles" not in st.session_state:
    st.session_state.articles = DEFAULT_ARTICLES.copy()

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

ADMIN_PASSWORD = "admin123"

# Sidebar
with st.sidebar:
    st.title("📚 Wiki AI & Data")
    st.markdown("---")
    
    titles = [art["title"] for art in st.session_state.articles]
    selected_title = st.selectbox("Chọn chủ đề:", ["-- Chọn bài viết --"] + titles)
    
    st.markdown("---")
    st.subheader("🔐 Admin")
    
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
        
        # Backup / Restore JSON
        data_json = json.dumps(st.session_state.articles, ensure_ascii=False, indent=2)
        st.download_button(
            label="Tải dữ liệu bài viết (JSON)",
            data=data_json,
            file_name="wiki_data.json",
            mime="application/json"
        )
        
        uploaded_json = st.file_uploader("Tải lên dữ liệu JSON", type="json", key="json_up")
        if uploaded_json is not None:
            try:
                new_data = json.load(uploaded_json)
                if isinstance(new_data, list):
                    st.session_state.articles = new_data
                    st.success("Đã cập nhật dữ liệu!")
                    st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")
        
        # === TẢI LÊN HÌNH & TÀI LIỆU VỚI TÊN MỤC RIÊNG ===
        st.markdown("---")
        st.subheader("📎 Tải lên File & Đặt Tên Mục")
        
        with st.form("upload_media_form"):
            custom_topic_name = st.text_input("Nhập tên mục / chủ đề riêng cho file:")
            uploaded_file = st.file_uploader(
                "Chọn hình ảnh
