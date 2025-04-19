import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import os # 引入 os 處理檔名

# --- fetch_sticker_info 函數保持不變 (同上一版本) ---
def fetch_sticker_info(url):
    """
    從 LINE Store URL 獲取貼圖資訊，包括靜態和動畫 URL。
    (此函數與上一版本相同，為保持完整性而複製於此)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 1.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    info = {
        "title": "N/A", "author": "N/A", "description": "N/A", "price": "N/A",
        "static_image_urls": [], "animation_urls": []
    }
    urls_found = set()

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- 提取基本資訊 ---
        title_tag = soup.find('p', class_='mdCMN38Item01Ttl')
        if title_tag: info['title'] = title_tag.get_text(strip=True)
        author_tag = soup.find('a', class_='mdCMN38Item01Author')
        if author_tag: info['author'] = author_tag.get_text(strip=True)
        desc_tag = soup.find('p', class_='mdCMN38Item01Txt')
        if desc_tag: info['description'] = desc_tag.get_text(strip=True)
        price_tag = soup.find('p', class_='mdCMN38Item01Price')
        if price_tag:
             price_text = price_tag.get_text(strip=True)
             if '免費' in price_text or 'None' in price_text: info['price'] = price_text
             else:
                 match = re.search(r'NT\$(\d+)', price_text)
                 info['price'] = f"NT${match.group(1)}" if match else price_text

        # --- 提取動畫 URL ---
        sticker_li_tags = soup.find_all('li', class_='FnStickerPreviewItem')
        for tag in sticker_li_tags:
            if 'data-preview' in tag.attrs:
                try:
                    preview_data = json.loads(tag['data-preview'])
                    if isinstance(preview_data, dict) and 'animationUrl' in preview_data:
                        anim_url = preview_data['animationUrl']
                        if anim_url and isinstance(anim_url, str) and anim_url not in urls_found:
                            info['animation_urls'].append(anim_url)
                            urls_found.add(anim_url)
                except json.JSONDecodeError: st.warning("解析 data-preview JSON 時出錯。")
                except Exception as e: st.warning(f"處理 data-preview 時發生未知錯誤: {e}")
        return info
    except requests.exceptions.RequestException as e: st.error(f"請求網頁時發生錯誤: {e}"); return None
    except Exception as e: st.error(f"處理網頁內容時發生錯誤: {e}"); return None

def get_content_and_filename(url, index):
    """
    下載指定 URL 的內容，並根據 Content-Type 或預設為 .gif 決定檔名。

    Args:
        url (str): 要下載的圖片 URL。
        index (int): 圖片的索引，用於生成唯一檔名。

    Returns:
        tuple: (content, filename, mime_type) 或 (None, None, None)
    """
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get('content-type', 'application/octet-stream').lower()
        content = response.content

        # 決定副檔名
        extension = ".gif" # 預設為 .gif
        if 'image/gif' in content_type:
            extension = ".gif"
        elif 'image/png' in content_type: # 可能是 APNG
            extension = ".png"
        elif 'image/webp' in content_type:
            extension = ".webp"
        elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
             extension = ".jpg"
        else:
            # 嘗試從 URL 提取原始副檔名 (如果有的話)
            try:
                path = url.split('?')[0] # 去掉查詢參數
                original_ext = os.path.splitext(path)[1]
                if original_ext and len(original_ext) <= 5: # 簡單檢查是否像副檔名
                    extension = original_ext
            except Exception:
                pass # 出錯就用預設的 .gif

        # 生成檔名 (例如 sticker_1.gif, sticker_2.png)
        filename = f"sticker_{index+1}{extension}"

        return content, filename, content_type
    except requests.exceptions.RequestException as e:
        st.error(f"下載 {url} 時發生錯誤: {e}", icon="🚨")
        return None, None, None
    except Exception as e:
        st.error(f"處理 {url} 時發生錯誤: {e}", icon="🚨")
        return None, None, None

# --- Streamlit App ---

st.set_page_config(page_title="LINE 貼圖資訊", layout="wide")
st.title("LINE 貼圖資訊顯示與下載")
st.caption(f"目前的網頁時間是: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

default_url = "https://store.line.me/stickershop/product/30397660/zh-Hant"
sticker_url = st.text_input("請輸入 LINE Store 貼圖網址：", default_url)

if st.button("取得貼圖資訊", key="fetch_button") or 'sticker_info' not in st.session_state or st.session_state.get('current_url') != sticker_url:
    if sticker_url:
        with st.spinner("正在爬取網頁並解析資訊..."):
            sticker_info = fetch_sticker_info(sticker_url)
            st.session_state['sticker_info'] = sticker_info
            st.session_state['current_url'] = sticker_url
    else:
        st.warning("請輸入有效的 URL")
        st.session_state['sticker_info'] = None

if 'sticker_info' in st.session_state and st.session_state['sticker_info']:
    info = st.session_state['sticker_info']

    # --- 顯示基本資訊 ---
    st.header(f"```{info['title']}```")
    st.write(f"**作者：** {info['author']}")
    st.write(f"**價格：** {info['price']}")
    st.write("**描述：**")
    st.info(info['description'])

    # --- 顯示動畫貼圖與下載按鈕 ---
    st.subheader("動畫貼圖預覽與下載：")
    if info['animation_urls']:
        num_animations = len(info['animation_urls'])
        st.write(f"找到 {num_animations} 個動畫貼圖 URL：")

        cols_per_row = 5 # 調整每行顯示數量
        rows = [info['animation_urls'][i:i + cols_per_row] for i in range(0, num_animations, cols_per_row)]

        for row_urls in rows:
            cols = st.columns(cols_per_row)
            for i, anim_url in enumerate(row_urls):
                with cols[i]:
                    # 使用 Markdown 的 img 標籤顯示，通常對動畫支援更好
                    st.markdown(f'<img src="{anim_url}" width="120">', unsafe_allow_html=True)

                    # 添加下載按鈕
                    # 為了避免重複下載，我們可以在按鈕點擊時才真正去下載
                    # 生成唯一的 key 給每個下載按鈕
                    button_key = f"download_{anim_url}_{i}"
                    # 預先獲取下載內容和檔名 (或者在按鈕點擊時才獲取)
                    # 為了簡化，我們先在這裡獲取
                    content, filename, mime_type = get_content_and_filename(anim_url, info['animation_urls'].index(anim_url))

                    if content and filename:
                        st.download_button(
                            label="下載 GIF/動畫",
                            data=content,
                            file_name=filename, # 使用檢測到的或預設的檔名
                            mime=mime_type, # 提供 MIME type
                            key=button_key # 唯一的 key
                        )
                    else:
                        st.caption("無法下載") # 如果 get_content_and_filename 失敗

                    # (可選) 顯示 URL 供參考
                    # st.caption(f"[URL]({anim_url})")

    else:
        st.warning("未找到動畫貼圖 URL。")

elif 'sticker_info' in st.session_state:
    st.error("無法獲取或處理貼圖資訊，請檢查 URL 或稍後再試。")

st.markdown("---")
st.caption("注意：本應用程式透過爬取 LINE Store 網頁獲取資訊，網頁結構變更可能導致功能失效。請遵守 LINE Store 使用條款。下載功能會根據伺服器回傳的 Content-Type 或預設為 .gif 副檔名。")