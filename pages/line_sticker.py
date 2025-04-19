# final_line_sticker_app.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import os # 引入 os 處理檔名
import base64 # <--- 匯入 base64 模組

# --- fetch_sticker_info 函數 ---
def fetch_sticker_info(url):
    """
    從 LINE Store URL 獲取貼圖資訊，包括靜態和動畫 URL。
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
        # 確保 URL 開頭為 https: (增加了輸入清理)
        url = url.strip()
        if not url.startswith("https:"):
            if url.startswith("http:"):
                url = url.replace("http:", "https:", 1)
                st.warning("已自動將 URL 修正為 https 格式。")
            else:
                match = re.search(r"https?://[^\s]+", url)
                if match:
                    url = match.group(0).replace("http:", "https:", 1)
                    st.warning("已從輸入中提取並修正 URL 為 https 格式。")
                else:
                    st.error("請輸入有效的 LINE Store 貼圖網址 (應以 'https://store.line.me/...' 開頭)。")
                    return None # 無法處理的 URL，返回 None

        response = requests.get(url, headers=headers, timeout=15) # 增加超時
        response.raise_for_status()
        response.encoding = response.apparent_encoding # 自動檢測編碼
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
             if '免費' in price_text or 'None' in price_text or not price_text: # 處理空價格
                 info['price'] = "免費或無需代幣"
             else:
                 # 優先匹配 NT$
                 match_ntd = re.search(r'NT\$(\d+)', price_text)
                 if match_ntd:
                     info['price'] = f"NT${match_ntd.group(1)}"
                 else:
                     # 其次匹配 代幣 (數字)
                     match_coin = re.search(r'(\d+)', price_text)
                     if match_coin:
                         info['price'] = f"{match_coin.group(1)} 代幣"
                     else:
                         info['price'] = price_text # 都沒匹配到，顯示原始文字

        # --- 提取動畫/聲音 URL (從 data-preview) ---
        sticker_li_tags = soup.find_all('li', class_='FnStickerPreviewItem') # 確保是這個 class
        for tag in sticker_li_tags:
            if 'data-preview' in tag.attrs:
                try:
                    preview_data = json.loads(tag['data-preview'])
                    if isinstance(preview_data, dict):
                        # 優先尋找動畫 URL
                        anim_url = preview_data.get('animationUrl') or preview_data.get('popupUrl') # 有些是 popup
                        if anim_url and isinstance(anim_url, str) and anim_url not in urls_found:
                             info['animation_urls'].append(anim_url)
                             urls_found.add(anim_url)
                             continue # 找到動畫就不用找靜態了

                        # 如果沒有動畫 URL，再找聲音 URL (通常也是動畫?)
                        sound_url = preview_data.get('soundUrl')
                        if sound_url and isinstance(sound_url, str) and sound_url not in urls_found:
                             info['animation_urls'].append(sound_url) # 也加到 animation_urls 裡
                             urls_found.add(sound_url)
                             continue

                        # 如果都沒有，最後找靜態 URL
                        static_url = preview_data.get('staticUrl')
                        if static_url and isinstance(static_url, str) and static_url not in urls_found:
                            info['static_image_urls'].append(static_url) # 放入靜態列表
                            urls_found.add(static_url)

                except json.JSONDecodeError:
                    st.warning(f"解析 data-preview JSON 時出錯: {tag['data-preview'][:100]}...") # 顯示部分錯誤內容
                except Exception as e:
                    st.warning(f"處理 data-preview 時發生未知錯誤: {e}")

        # 如果 animation_urls 是空的，但 static_urls 有內容，把 static 移過去當作主要顯示
        if not info['animation_urls'] and info['static_image_urls']:
             st.info("未找到特定動畫 URL，將顯示靜態貼圖。")
             info['animation_urls'] = info['static_image_urls']
             info['static_image_urls'] = [] # 清空靜態

        return info
    except requests.exceptions.Timeout:
        st.error("請求網頁超時，請稍後再試或檢查網路連線。")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"請求網頁時發生錯誤: {e}")
        return None
    except Exception as e:
        st.error(f"處理網頁內容時發生嚴重錯誤: {e}")
        return None


# --- get_content_and_filename 函數 (用於下載按鈕) ---
def get_content_and_filename(url, index):
    """
    下載指定 URL 的內容，並強制將檔名設為 .gif。
    """
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        content = response.content
        extension = ".gif"
        filename = f"sticker_{index+1}{extension}" # 檔名從 1 開始
        mime_type = "image/gif"
        return content, filename, mime_type
    except requests.exceptions.RequestException as e:
        print(f"錯誤：下載 {url} 失敗: {e}")
        return None, None, None
    except Exception as e:
        print(f"錯誤：處理 {url} 失敗: {e}")
        return None, None, None

# --- 新增函數：獲取圖片內容並轉為 Data URI ---
def get_image_as_data_uri(url):
    """
    下載圖片內容並轉換為 data:image/gif;base64 格式的 URI。
    """
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        content = response.content
        encoded_content = base64.b64encode(content).decode('utf-8')
        data_uri = f"data:image/gif;base64,{encoded_content}"
        return data_uri
    except Exception as e:
        print(f"錯誤：轉換 Data URI 失敗 {url}: {e}")
        return None # 返回 None 表示失敗


# --- Streamlit App ---

# 頁面配置應只調用一次，最好放在腳本開頭
st.set_page_config(page_title="LINE 貼圖資訊", layout="wide")

st.title("LINE 貼圖資訊顯示與下載 🚀")
st.caption(f"目前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 使用 session state 來儲存 URL，避免重複輸入
if 'sticker_url' not in st.session_state:
    st.session_state.sticker_url = "https://store.line.me/stickershop/product/30397660/zh-Hant" # 預設值

# URL 輸入框
sticker_url_input = st.text_input(
    "請輸入 LINE Store 貼圖網址：",
    st.session_state.sticker_url, # 使用 session state 中的值
    key="sticker_url_input_key", # 給一個 key
    placeholder="例如: https://store.line.me/stickershop/product/12345/zh-Hant"
)

# 當輸入框的值改變時，更新 session state
st.session_state.sticker_url = sticker_url_input

# 觸發按鈕 和 判斷 URL 是否變更 或 首次加載
# 將 'sticker_info' 初始化為 None，如果它還不存在
if 'sticker_info' not in st.session_state:
    st.session_state.sticker_info = None
if 'current_processed_url' not in st.session_state:
    st.session_state.current_processed_url = None


fetch_needed = False
if st.button("① 取得貼圖資訊", key="fetch_button"):
     fetch_needed = True
elif st.session_state.sticker_info is None: # 如果還沒有資訊，且使用者提供了 URL
     if st.session_state.sticker_url:
         fetch_needed = True
elif st.session_state.current_processed_url != st.session_state.sticker_url: # 如果 URL 變了
     fetch_needed = True


if fetch_needed and st.session_state.sticker_url:
    with st.spinner("⚙️ 正在爬取網頁並解析資訊..."):
        sticker_info_result = fetch_sticker_info(st.session_state.sticker_url)
        st.session_state.sticker_info = sticker_info_result # 儲存結果 (可能是 None)
        st.session_state.current_processed_url = st.session_state.sticker_url # 記錄已處理的 URL
        # 清除舊的預處理資料 (如果有的話)
        if 'image_data_uris' in st.session_state:
            del st.session_state['image_data_uris']
        if 'download_data' in st.session_state:
            del st.session_state['download_data']

elif fetch_needed and not st.session_state.sticker_url:
    st.warning("請先輸入有效的 LINE Store 貼圖網址。")
    st.session_state.sticker_info = None # 清空舊資訊


# --- 顯示結果 ---
# 檢查 session state 中是否有有效的貼圖資訊
if 'sticker_info' in st.session_state and st.session_state.sticker_info:
    info = st.session_state.sticker_info # 從 session state 取出資訊

    # --- 顯示基本資訊 ---
    st.header(f"```{info.get('title', '標題未知')}```") # 使用 .get 提供預設值
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**作者：** {info.get('author', '作者未知')}")
    with col2:
        st.write(f"**價格：** {info.get('price', '價格未知')}")

    st.write("**描述：**")
    # 使用 expander 隱藏較長的描述
    with st.expander("點此查看描述", expanded=False):
         st.info(info.get('description', '無描述'))

    # --- 顯示動畫貼圖與下載按鈕 ---
    st.subheader("② 貼圖預覽與下載：")

    # 使用 'animation_urls' 這個 key，即使裡面放的是靜態的
    image_urls_to_display = info.get('animation_urls', [])

    if image_urls_to_display:
        num_images = len(image_urls_to_display)
        st.write(f"找到 {num_images} 個貼圖。")

        # --- 預處理 Data URIs 和下載資料 ---
        # 檢查是否已經在 session state 中，避免重複處理
        if 'image_data_uris' not in st.session_state or 'download_data' not in st.session_state:
            st.session_state.image_data_uris = {}
            st.session_state.download_data = {}
            with st.spinner(f"⏳ 正在準備 {num_images} 個貼圖預覽 (這可能需要一點時間)..."):
                for index, img_url in enumerate(image_urls_to_display):
                    # 獲取 Data URI 用於顯示
                    data_uri = get_image_as_data_uri(img_url)
                    st.session_state.image_data_uris[img_url] = data_uri # 存入 session state

                    # 獲取下載按鈕的內容和檔名
                    content, filename, mime_type = get_content_and_filename(img_url, index)
                    if content:
                        st.session_state.download_data[img_url] = {"content": content, "filename": filename, "mime": mime_type}
                    else:
                         st.session_state.download_data[img_url] = None # 標記失敗


        # --- 分行顯示 ---
        cols_per_row = st.slider("每行顯示數量", min_value=3, max_value=10, value=6) # 讓使用者調整
        # 計算總行數
        total_rows = (num_images + cols_per_row - 1) // cols_per_row

        for row_index in range(total_rows):
            # 取得當前行的圖片 URL
            start_index = row_index * cols_per_row
            end_index = min(start_index + cols_per_row, num_images)
            row_urls = image_urls_to_display[start_index:end_index]

            # 創建列
            cols = st.columns(cols_per_row)

            for i, img_url in enumerate(row_urls):
                with cols[i]:
                    # 從 session state 取出 Data URI
                    data_uri_to_display = st.session_state.image_data_uris.get(img_url)

                    if data_uri_to_display:
                        # 使用 Data URI 作為 src，強制瀏覽器以 GIF 解讀
                        st.markdown(f'<img src="{data_uri_to_display}" width="120">', unsafe_allow_html=True)
                    else:
                        st.caption(f"無法載入預覽")
                        st.markdown(f'[原始連結]({img_url})', unsafe_allow_html=True)

                    # --- 下載按鈕邏輯 ---
                    # 計算這個貼圖在原始列表中的絕對索引
                    current_original_index = start_index + i
                    button_key = f"download_{current_original_index}" # 使用原始索引確保 key 唯一

                    # 從 session state 取出下載資訊
                    dl_info = st.session_state.download_data.get(img_url)

                    if dl_info:
                        st.download_button(
                            label="下載 GIF",
                            data=dl_info["content"],
                            file_name=dl_info["filename"],
                            mime=dl_info["mime"],
                            key=button_key,
                            help=f"下載 {dl_info['filename']}" # 增加提示
                        )
                    else:
                        st.caption("無法下載")

            # 在行與行之間添加一些間隔
            st.write("---")


    else: # 如果 info['animation_urls'] 是空的或不存在
        st.warning("在此 URL 未找到可顯示的貼圖。")

# 處理 fetch_sticker_info 返回 None 的情況 (例如網路錯誤、URL 無效)
elif 'sticker_info' in st.session_state and st.session_state.sticker_info is None and fetch_needed:
    # 錯誤訊息已經由 fetch_sticker_info 顯示了
    # st.error("無法獲取貼圖資訊，請檢查輸入的 URL 或網路連線。")
    pass # 保持介面簡潔

# --- 頁腳 ---
st.markdown("---")
st.caption("注意：本工具透過爬取 LINE Store 網頁獲取公開資訊，網頁結構變更可能導致功能失效。請尊重版權並遵守 LINE Store 使用條款。下載功能強制以 .gif 副檔名儲存。")