# -*- coding: utf-8 -*-
"""
app.py — Wiki AI & Data + Multi-Source Scraper + Supabase Persistent Backend
Hệ thống kho tri thức kết nối cơ sở dữ liệu đám mây Supabase vĩnh viễn.
"""

import streamlit as st
import json
from datetime import datetime
import hashlib
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from supabase import create_client

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
# 2. KẾT NỐI SUPABASE & QUẢN LÝ DỮ LIỆU
# ==========================================
def get_supabase_client():
    """Khởi tạo kết nối tới Supabase Database"""
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        if not url or not key:
            return None
        # Tự động loại bỏ khoảng trắng hoặc dấu / dư ở cuối URL để tránh lỗi kết nối httpx
        url = url.strip().rstrip('/')
        return create_client(url, key)
    except Exception as e:
        print(f"Lỗi khởi tạo Supabase: {e}")
        return None

def load_database():
    """Tải toàn bộ kho tri thức từ Supabase"""
    client = get_supabase_client()
    if not client:
        return []
    try:
        response = client.table("wiki_knowledge").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Lỗi tải dữ liệu từ Supabase: {e}")
        return []

def save_database(articles):
    """Lưu và cập nhật danh sách bài viết lên Supabase"""
    client = get_supabase_client()
    if not client:
        st.error("❌ Chưa cấu hình SUPABASE_URL hoặc SUPABASE_KEY trong Secrets!")
        return False
    try:
        for art in articles:
            client.table("wiki_knowledge").upsert(art).execute()
        st.toast("Đã đồng bộ vĩnh viễn lên Supabase thành công!", icon="🚀")
        return True
    except Exception as e:
        st.error(f"❌ Lỗi lưu dữ liệu lên Supabase: {e}")
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
    client = get_supabase_client()
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
    if client:
        client.table("wiki_knowledge").upsert(new_art).execute()
    return new_art["id"]

# ==========================================
# 4. BOT CÀO DỮ LIỆU TỪ NHIỀU NGUỒN (MULTI-SOURCE SCRAPER)
# ==========================================
class MultiSourceScraperBot:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64
