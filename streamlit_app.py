# -*- coding: utf-8 -*-
"""
app.py — Wiki AI & Data + Multi-Source Scraper + GitHub JSON Persistent Backend
Hệ thống kho tri thức lưu trữ vĩnh viễn trên GitHub Cloud, chống mọi lỗi kết nối mạng.
"""

import streamlit as st
import json
from datetime import datetime
import hashlib
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
base64 = __import__('base64')

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & GIỚI HẠN UPLOAD 1GB
# ==========================================
os.makedirs(".streamlit", exist_ok=True)
with open(".streamlit/config.toml", "w") as f:
    f.write("[server]\nmaxUploadSize = 1024\n")

st.set_page_config(page_title="Wiki AI & Data - AGI Knowledge Engine", page_icon="📚", layout="wide")

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
    [data-testid="stFileUploader"] section small {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. KẾT NỐI GITHUB CLOUD & QUẢN LÝ DỮ LIỆU
# ==========================================
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "urgayhaha/chatbot")  # Repo của sếp
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
JSON_FILE_PATH = "wiki_database.json"

def load_database():
    """Tải toàn bộ kho tri thức từ GitHub Cloud JSON"""
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{JSON_FILE_PATH}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Lỗi tải dữ liệu từ GitHub: {e}")
    return []

def save_database(articles):
    """Lưu và đồng bộ danh sách bài viết lên GitHub Cloud"""
    if not GITHUB_TOKEN:
        st.error("❌ Chưa cấu hình GITHUB_TOKEN trong Secrets!")
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{JSON_FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    try:
        # Lấy sha hiện tại của file (nếu có)
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None
        
        # Chuẩn bị nội dung mã hóa base64
        content_str = json.dumps(articles, ensure_ascii=False, indent=4)
        content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        
        payload = {
            "message": "Update wiki database via Streamlit Cloud",
            "content": content_b64,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha
            
        res = requests.put(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            st.toast("Đã đồng bộ vĩnh viễn lên GitHub Cloud thành công!", icon="🚀")
            return True
        else:
            st.error(f"❌ Lỗi lưu GitHub: {res.text}")
            return False
    except Exception as e:
        st.error(f"❌ Lỗi kết nối GitHub API: {e}")
        return False

def make_id(title):
    return hashlib.md5((title + str(datetime.now().timestamp())).encode()).hexdigest()[:10]

# ==========================================
# 3. HÀM API TRỰC TIẾP CHO AGI (AGI DIRECT ACCESS API)
# ==========================================
def agi_get_all_articles():
    return load_database()

def agi_search_article(keyword):
    data = load_database()
    keyword = keyword.lower()
    return [art for art in data if keyword in art.get("title", "").lower() or keyword in art.get("content", "").lower()]

def agi_add_article(title, content, source="AGI Agent"):
    db = load_database()
    new_art = {
        "id": make_id(title),
        "title": title.strip(),
        "content": content,
        "source": source,
        "source_url": "#",
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "type": "text",
        "files_list": []
    }
    db.append(new_art)
    save_database(db)
    return new_art["id"]

# ==========================================
# 4. BOT CÀO DỮ LIỆU TỪ NHIỀU NGUỒN (MULTI-SOURCE SCRAPER)
# ==========================================
class MultiSourceScraperBot:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

    def scrape_web_page(self, url):
        try:
            parsed_url = urlparse(url)
            domain_source = parsed_url.netloc if parsed_url.netloc else "Web ngoài"

            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                title_tag = soup.find("h1") or soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else "Bài viết không tiêu đề"
                
                paragraphs = soup.find_all("p")
                content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
                
                if not content:
                    content = "Không thể trích xuất nội dung chi tiết từ trang này."

                return {
                    "title": title[:150],
                    "content": content,
                    "source": domain_source,
                    "source_url": url
                }
        except Exception as e:
            print(f"Lỗi cào dữ liệu từ {url}: {e}")
        return None

    def run_multi_source_crawl(self, url_list):
        db = load_database()
        added_count = 0

        for url in url_list:
            url = url.strip()
            if not url:
                continue
            
            if any(item.get("source_url") == url for item in db):
                continue

            scraped_data = self.scrape_web_page(url)
            if scraped_data:
                new_entry = {
                    "id": make_id(scraped_data["title"]),
                    "title": scraped_data["title"],
                    "content": scraped_data["content"],
                    "source": scraped_data["source"],
                    "source_url": scraped_data["source_url"],
                    "updated": datetime.now().strftime("%Y-%m-%d"),
                    "type": "text",
                    "files_list": []
                }
                db.append(new_entry)
                added_count += 1

        if added_count > 0:
            save_database(db)

        return added_count

# ==========================================
# 5. GIAO DIỆN WEB STREAMLIT
# ==========================================
st.markdown("<h1 style='text-align:center;'>Wiki về AI và tài liệu</h1>", unsafe_allow_html=True)

# Thanh menu popover ở góc phải trên cùng
_, col_btn = st.columns([11, 1])
with col_btn:
    with st.popover("☰"):
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

                    db_data = load_database()

                    for jf in json_files:
                        try:
                            data = json.load(jf)
                            if isinstance(data, list):
                                db_data.extend(data)
                                save_database(db_data)
                                st.success("Đã tải JSON và đồng bộ GitHub Cloud!")
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
                        db_data.append(new_entry)
                        save_database(db_data)
                        st.success(f"Đã tạo và đồng bộ GitHub Cloud: {ten_muc.strip()}")
                    elif other_files:
                        st.warning("Vui lòng nhập tên mục trước khi tải lên.")
                    st.rerun()

        st.markdown("---")
        st.markdown("**🤖 Bot Cào Dữ Liệu Tự Động**")
        with st.form("scraper_form"):
            urls_input = st.text_area("Nhập URL nguồn (mỗi dòng 1 URL):", placeholder="https://example.com/bai-viet-1")
            if st.form_submit_button("Chạy Bot Cào & Lưu"):
                if urls_input.strip():
                    url_list = urls_input.split("\n")
                    bot = MultiSourceScraperBot()
                    with st.spinner("Bot đang đi cào dữ liệu từ các nguồn..."):
                        count = bot.run_multi_source_crawl(url_list)
                    st.success(f"Đã cào thành công và đồng bộ vĩnh viễn {count} mục lên GitHub Cloud!")
                    st.rerun()
                else:
                    st.warning("Vui lòng nhập ít nhất một URL hợp lệ.")

# ==========================================
# 6. HIỂN THỊ DANH SÁCH DẠNG MỤC MỞ RỘNG (EXPANDER)
# ==========================================
current_articles = load_database()

st.markdown("---")
if current_articles:
    st.markdown("### 📚 Danh sách các mục tri thức:")
    for idx, art in enumerate(current_articles):
        title = art.get('title', 'Không tiêu đề')
        source = art.get('source', 'Không rõ')
        updated = art.get('updated', '')
        
        with st.expander(f"📖 {title} — [Nguồn: {source}] (Cập nhật: {updated})"):
            if art.get("type") == "multi_media":
                for f in art.get("files_list", []):
                    st.write(f"**Tệp đính kèm:** {f.get('file_name')} ({f.get('file_size', 0)} bytes)")
                    st.markdown("---")
            else:
                st.write(art.get("content", ""))

            if art.get("type") != "multi_media":
                st.markdown("---")
                st.subheader("Chỉnh sửa nội dung mục này")
                with st.form(f"edit_{art.get('id')}_{idx}"):
                    new_title = st.text_input("Tiêu đề", value=art.get("title", ""), max_chars=1000)
                    new_content = st.text_area("Nội dung", value=art.get("content", ""), height=150)
                    if st.form_submit_button("Lưu thay đổi"):
                        art["title"] = new_title
                        art["content"] = new_content
                        art["updated"] = datetime.now().strftime("%Y-%m-%d")
                        # Cập nhật trong list
                        for i, item in enumerate(current_articles):
                            if item.get("id") == art.get("id"):
                                current_articles[i] = art
                        save_database(current_articles)
                        st.success("Đã lưu và đồng bộ thay đổi lên GitHub Cloud!")
                        st.rerun()
else:
    st.info("Kho tri thức hiện đang trống. Hãy nhấn vào biểu tượng menu (☰) ở góc trên bên phải để tải tệp lên hoặc sử dụng Bot Cào dữ liệu.")
