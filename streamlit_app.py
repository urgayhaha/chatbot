# -*- coding: utf-8 -*-
"""
Wiki AI & Data — lưu vĩnh viễn qua GitHub (dùng trên Streamlit Cloud).

Streamlit Cloud xóa file local mỗi lần restart. App này ghi wiki_database.json
lên GitHub rồi đọc lại, nên dữ liệu còn sau khi app ngủ hoặc khởi động lại.

Secrets (Streamlit Cloud → Settings → Secrets), không dán token vào code:

GITHUB_TOKEN = "github_pat_..."
GITHUB_REPO = "username/ten-repo"
GITHUB_BRANCH = "main"

Token: GitHub → Settings → Developer settings → Fine-grained hoặc classic PAT,
quyền Contents: Read and write trên đúng repo đó.
"""
import base64
import hashlib
import json
import os
from datetime import datetime
from urllib.parse import urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Wiki AI & Data", page_icon="📚", layout="wide")

DB_FILE = "wiki_database.json"
MAX_FILE_BYTES = 350_000
MAX_DB_BYTES = 900_000

st.markdown(
    """
<style>
    .main { background-color: #f8f9fa; }
    h1 { color: #1e3a5f; text-align: center; margin-bottom: 8px; }
    div.stFormSubmitButton > button {
        background-color: #0b63ce !important;
        color: white !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


def _gh_cfg():
    try:
        token = st.secrets.get("GITHUB_TOKEN") or ""
        repo = st.secrets.get("GITHUB_REPO") or ""
        branch = st.secrets.get("GITHUB_BRANCH") or "main"
    except Exception:
        return "", "", "main"
    return str(token).strip(), str(repo).strip(), str(branch).strip() or "main"


def gh_configured():
    token, repo, _ = _gh_cfg()
    return bool(token and repo and "github_pat" not in token.lower() or (token and repo))


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _decode_file(payload):
    raw = payload.get("content") or ""
    if not raw:
        return []
    text = base64.b64decode(raw).decode("utf-8")
    data = json.loads(text)
    return data if isinstance(data, list) else []


def fetch_remote():
    """Đọc database trên GitHub. None = lỗi mạng / token. [] = chưa có file."""
    token, repo, branch = _gh_cfg()
    if not token or not repo:
        return None, "Chưa có GITHUB_TOKEN hoặc GITHUB_REPO trong Secrets."
    url = f"https://api.github.com/repos/{repo}/contents/{DB_FILE}"
    try:
        r = requests.get(url, headers=_headers(token), params={"ref": branch}, timeout=20)
    except Exception as e:
        return None, f"Không gọi được GitHub: {e}"
    if r.status_code == 200:
        body = r.json()
        if body.get("encoding") != "base64" or not body.get("content"):
            return None, "File trên GitHub quá lớn hoặc GitHub không trả nội dung (giới hạn ~1 MB)."
        try:
            return _decode_file(body), None
        except Exception as e:
            return None, f"File GitHub không phải JSON hợp lệ: {e}"
    if r.status_code == 404:
        return [], None
    return None, f"GitHub trả {r.status_code}: {r.text[:180]}"


def push_remote(articles, retries=2):
    token, repo, branch = _gh_cfg()
    if not token or not repo:
        return False, "Thiếu Secrets GitHub. Dữ liệu chỉ nằm trong phiên này và sẽ mất khi restart."

    blob = json.dumps(articles, ensure_ascii=False, indent=2).encode("utf-8")
    if len(blob) > MAX_DB_BYTES:
        return False, f"Database {len(blob)//1024} KB, vượt giới hạn an toàn {MAX_DB_BYTES//1024} KB của GitHub Contents API."

    url = f"https://api.github.com/repos/{repo}/contents/{DB_FILE}"
    headers = _headers(token)
    last_err = "Không rõ"
    for _ in range(retries):
        try:
            current = requests.get(url, headers=headers, params={"ref": branch}, timeout=20)
        except Exception as e:
            return False, f"Không đọc được file hiện tại: {e}"

        sha = None
        remote = []
        if current.status_code == 200:
            info = current.json()
            sha = info.get("sha")
            try:
                remote = _decode_file(info)
            except Exception:
                remote = []
        elif current.status_code != 404:
            return False, f"GitHub đọc file lỗi {current.status_code}: {current.text[:180]}"

        deleted = set(st.session_state.get("deleted_ids") or [])
        by_id = {}
        for item in remote:
            iid = item.get("id")
            if iid and iid not in deleted:
                by_id[iid] = item
        for item in articles:
            iid = item.get("id")
            if iid and iid not in deleted:
                by_id[iid] = item
        merged = list(by_id.values())

        payload = {
            "message": f"wiki update {datetime.now():%Y-%m-%d %H:%M:%S}",
            "content": base64.b64encode(
                json.dumps(merged, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        try:
            put = requests.put(url, headers=headers, json=payload, timeout=25)
        except Exception as e:
            return False, f"Không đẩy được lên GitHub: {e}"
        if put.status_code in (200, 201):
            st.session_state.articles = merged
            st.session_state.deleted_ids = set()
            return True, None
        last_err = f"{put.status_code}: {put.text[:180]}"
        if put.status_code != 409:
            break
    return False, f"GitHub từ chối ghi. {last_err}"


def load_database():
    if st.session_state.get("articles") is not None:
        return st.session_state.articles
    remote, err = fetch_remote()
    if remote is not None:
        st.session_state.articles = remote
        st.session_state.gh_error = None
        return remote
    st.session_state.gh_error = err
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                st.session_state.articles = data
                return data
        except Exception:
            pass
    st.session_state.articles = []
    return []


def save_database(articles):
    st.session_state.articles = articles
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    ok, err = push_remote(articles)
    if ok:
        st.toast("Đã lưu lên GitHub. Restart app vẫn còn dữ liệu.")
    else:
        st.session_state.gh_error = err
        st.warning(err)
    return ok


def make_id(title):
    raw = f"{title}|{datetime.now().timestamp()}|{os.urandom(4).hex()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def agi_add_article(title, content, source="AGI Agent"):
    """Hàm để bot/AGI gọi: nạp một bài chữ vào wiki và đẩy GitHub."""
    data = load_database()
    art = {
        "id": make_id(title),
        "title": title.strip()[:300],
        "content": content,
        "source": source,
        "source_url": "#",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type": "text",
    }
    data.append(art)
    save_database(data)
    return art["id"]


class ScraperBot:
    def __init__(self):
        self.h = {"User-Agent": "WikiAI/1.0 (educational; +https://streamlit.io)"}

    def scrape(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None
        try:
            r = requests.get(url, headers=self.h, timeout=12)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            heading = soup.find("h1") or soup.find("title")
            title = heading.get_text(strip=True)[:180] if heading else parsed.netloc
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in soup.find_all("p")
                if len(p.get_text(strip=True)) > 40
            ]
            content = "\n\n".join(paragraphs)[:12000] or "Không trích được đoạn văn."
            return {
                "title": title,
                "content": content,
                "source": parsed.netloc,
                "source_url": url,
            }
        except Exception as e:
            st.error(f"Không cào được {url}: {e}")
            return None

    def run(self, urls):
        db = load_database()
        known = {a.get("source_url") for a in db}
        added = 0
        for url in urls:
            url = url.strip()
            if not url or url in known:
                continue
            item = self.scrape(url)
            if not item:
                continue
            db.append(
                {
                    "id": make_id(item["title"]),
                    **item,
                    "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "text",
                }
            )
            known.add(url)
            added += 1
        if added:
            save_database(db)
        return added


def _file_record(uploaded, title):
    raw = uploaded.getvalue()
    rec = {
        "file_name": uploaded.name,
        "file_type": uploaded.type or "application/octet-stream",
        "file_size": len(raw),
    }
    if len(raw) <= MAX_FILE_BYTES:
        rec["file_b64"] = base64.b64encode(raw).decode("ascii")
    else:
        rec["skipped"] = True
    rec["title_group"] = title
    return rec


st.markdown("<h1>Wiki về AI và tài liệu</h1>", unsafe_allow_html=True)

token_ok = gh_configured()
if token_ok:
    st.success("Đã thấy GitHub Secrets. Bài viết sẽ được đẩy lên repo và còn sau khi Streamlit Cloud restart.")
else:
    st.error("Chưa cấu hình GitHub Secrets. Dữ liệu trên Streamlit Cloud sẽ mất khi app restart.")

with st.expander("Cách bật lưu vĩnh viễn trên Streamlit Cloud"):
    st.markdown(
        """
1. Tạo một repo GitHub trống (có nhánh `main`).
2. Tạo Personal Access Token có quyền **ghi Contents** của repo đó.
3. Mở app trên Streamlit Cloud → **Settings → Secrets**.
4. Dán 3 dòng bên dưới (không bọc trong khung code), bấm **Save**, rồi **Reboot app**.
5. Thêm bài hoặc tải file. Trong repo phải xuất hiện `wiki_database.json`.
        """
    )
    st.text('GITHUB_TOKEN = "github_pat_xxxx"')
    st.text('GITHUB_REPO = "username/ten-repo"')
    st.text('GITHUB_BRANCH = "main"')
    st.caption(
        "File lớn hơn khoảng 350 KB không lưu nội dung. Cả database nên dưới khoảng 900 KB."
    )

menu, _ = st.columns([1, 5])
with menu:
    with st.popover("Thêm dữ liệu"):
        st.markdown("**Viết bài**")
        with st.form("manual_add", clear_on_submit=True):
            title_in = st.text_input("Tiêu đề")
            body_in = st.text_area("Nội dung", height=140)
            if st.form_submit_button("Lưu bài"):
                if title_in.strip() and body_in.strip():
                    agi_add_article(title_in, body_in, source="Nhập tay")
                    st.rerun()
                else:
                    st.warning("Cần cả tiêu đề và nội dung.")

        st.markdown("**Tải tệp**")
        with st.form("upload", clear_on_submit=True):
            ten_muc = st.text_input("Tên mục")
            files = st.file_uploader("Tệp", accept_multiple_files=True, label_visibility="collapsed")
            if st.form_submit_button("Tải lên") and files:
                db = load_database()
                json_files = [f for f in files if f.name.lower().endswith(".json")]
                other = [f for f in files if f not in json_files]
                ids = {a.get("id") for a in db}
                for jf in json_files:
                    try:
                        data = json.load(jf)
                        rows = data if isinstance(data, list) else [data]
                        for item in rows:
                            if not isinstance(item, dict):
                                continue
                            if "id" not in item:
                                item["id"] = make_id(item.get("title", "item"))
                            if item["id"] not in ids:
                                db.append(item)
                                ids.add(item["id"])
                    except Exception as e:
                        st.error(f"JSON lỗi: {e}")
                if other:
                    if not ten_muc.strip():
                        st.warning("Nhập tên mục cho tệp không phải JSON.")
                    else:
                        packed = [_file_record(f, ten_muc.strip()) for f in other]
                        skipped = [p["file_name"] for p in packed if p.get("skipped")]
                        db.append(
                            {
                                "id": make_id(ten_muc),
                                "title": ten_muc.strip(),
                                "source": "User Upload",
                                "source_url": "#",
                                "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "type": "multi_media",
                                "files_list": packed,
                            }
                        )
                        if skipped:
                            st.warning("Bỏ nội dung file quá lớn: " + ", ".join(skipped))
                save_database(db)
                st.rerun()

        st.markdown("**Cào trang web**")
        with st.form("scraper"):
            urls = st.text_area("Mỗi dòng một URL", placeholder="https://vi.wikipedia.org/wiki/Tri_tue_nhan_tao")
            if st.form_submit_button("Chạy"):
                if urls.strip():
                    with st.spinner("Đang lấy nội dung..."):
                        n = ScraperBot().run(urls.splitlines())
                    st.success(f"Đã thêm {n} trang.")
                    st.rerun()
                else:
                    st.warning("Chưa có URL.")

articles = load_database()
if st.session_state.get("gh_error") and token_ok:
    st.warning(st.session_state.gh_error)

q = st.text_input("Tìm trong wiki", placeholder="Từ khóa tiêu đề hoặc nội dung")
shown = articles
if q.strip():
    key = q.strip().lower()
    shown = [
        a
        for a in articles
        if key in str(a.get("title", "")).lower() or key in str(a.get("content", "")).lower()
    ]

st.markdown(f"### {len(shown)} mục")
if not shown:
    st.info("Kho đang trống, hoặc không khớp từ khóa. Mở “Thêm dữ liệu”.")

for i, art in enumerate(shown):
    label = f"{art.get('title', 'Không tiêu đề')} — {art.get('source', '?')} ({art.get('updated', '')})"
    with st.expander(label):
        if art.get("type") == "multi_media":
            for f in art.get("files_list") or []:
                st.write(f"{f.get('file_name')} — {f.get('file_size', 0)} bytes")
                b64 = f.get("file_b64")
                if b64:
                    st.download_button(
                        "Tải lại file",
                        data=base64.b64decode(b64),
                        file_name=f.get("file_name") or "file",
                        mime=f.get("file_type") or "application/octet-stream",
                        key=f"dl_{art.get('id')}_{f.get('file_name')}_{i}",
                    )
                elif f.get("skipped"):
                    st.caption("File này quá lớn nên không lưu nội dung.")
        else:
            st.write(art.get("content") or "")
            if art.get("source_url") and art.get("source_url") != "#":
                st.caption(art["source_url"])

        with st.form(f"edit_{art.get('id')}_{i}"):
            nt = st.text_input("Tiêu đề", value=art.get("title", ""), max_chars=300)
            nc = st.text_area("Nội dung", value=art.get("content", "") if art.get("type") != "multi_media" else "", height=160)
            save_clicked = st.form_submit_button("Lưu sửa")
        if save_clicked:
            art["title"] = nt.strip() or art.get("title")
            if art.get("type") != "multi_media":
                art["content"] = nc
            art["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_database(articles)
            st.rerun()

        if st.button("Xóa mục này", key=f"del_{art.get('id')}_{i}"):
            st.session_state.setdefault("deleted_ids", set()).add(art.get("id"))
            remain = [a for a in articles if a.get("id") != art.get("id")]
            save_database(remain)
            st.rerun()
