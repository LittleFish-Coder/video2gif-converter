import streamlit as st
from moviepy.editor import VideoFileClip
import tempfile
import os

# --- Streamlit App Configuration ---
st.set_page_config(
    page_title="影片轉 GIF 工具",
    page_icon="🎬",
    layout="centered" # 'wide' or 'centered'
)

# --- Functions ---
def convert_video_to_gif(input_video_path, output_gif_path, fps=10):
    """
    將影片檔案轉換為 GIF。

    Args:
        input_video_path (str): 輸入影片檔案的路徑。
        output_gif_path (str): 輸出 GIF 檔案的路徑。
        fps (int): GIF 的每秒影格數。

    Returns:
        bool: 轉換成功返回 True，否則返回 False。
    """
    try:
        # 讀取影片檔案
        clip = VideoFileClip(input_video_path)

        # 設定 FPS 並寫入 GIF 檔案
        # 可以加入更多參數，例如：
        # clip.subclip(t_start, t_end) # 截取片段
        # clip.resize(width=320) # 調整大小
        clip.write_gif(output_gif_path, fps=fps)

        # 關閉 clip 釋放資源
        clip.close()
        return True
    except Exception as e:
        st.error(f"轉換過程中發生錯誤： {e}")
        # 如果 clip 物件已建立但 write_gif 失敗，也嘗試關閉它
        if 'clip' in locals() and clip:
            try:
                clip.close()
            except Exception as close_err:
                st.warning(f"關閉影片 clip 時發生錯誤: {close_err}")
        return False

# --- Streamlit UI ---
st.title("🎬 影片轉換 GIF 小工具")
st.write("上傳你的影片檔案，設定 FPS，然後點擊轉換按鈕！")

# 1. 檔案上傳
uploaded_file = st.file_uploader(
    "選擇一個影片檔案",
    type=["mp4", "mov", "avi", "mkv", "wmv"], # 可以接受的影片格式
    help="支援 MP4, MOV, AVI, MKV, WMV 等格式"
)

# 暫存檔案的路徑變數
temp_video_path = None
temp_gif_path = None

if uploaded_file is not None:
    # 顯示上傳的影片資訊
    st.write("---")
    st.write("✅ 已上傳檔案:", uploaded_file.name)
    st.video(uploaded_file) # 直接顯示上傳的影片預覽

    # 2. 設定 GIF 參數
    st.write("---")
    st.subheader("GIF 設定")
    # 設定 FPS (Frames Per Second)
    fps = st.slider("選擇 GIF 的 FPS (每秒影格數)", min_value=1, max_value=30, value=10, step=1,
                    help="較高的 FPS 會讓 GIF 更流暢，但檔案也會更大。")

    # 3. 轉換按鈕
    st.write("---")
    convert_button = st.button("🚀 開始轉換成 GIF")

    if convert_button:
        # 使用 tempfile 來安全地處理臨時檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
            temp_video.write(uploaded_file.read())
            temp_video_path = temp_video.name # 取得暫存影片檔的路徑

        # 建立一個臨時的 GIF 輸出路徑
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as temp_gif:
            temp_gif_path = temp_gif.name

        if temp_video_path and temp_gif_path:
            # 顯示處理中訊息
            with st.spinner(f"正在將影片轉換為 {fps} FPS 的 GIF，請稍候..."):
                success = convert_video_to_gif(temp_video_path, temp_gif_path, fps)

            if success:
                st.success("🎉 GIF 轉換成功！")

                # 4. 顯示與下載 GIF
                # 讀取生成的 GIF 檔案內容以供顯示和下載
                with open(temp_gif_path, "rb") as f:
                    gif_bytes = f.read()

                st.image(gif_bytes, caption=f"生成的 GIF ({fps} FPS)")

                # 提供下載按鈕
                st.download_button(
                    label="📥 下載 GIF",
                    data=gif_bytes,
                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}_{fps}fps.gif", # 設定下載的檔名
                    mime="image/gif"
                )
            else:
                st.error("❌ GIF 轉換失敗，請檢查影片檔案或稍後再試。")

        # 清理臨時檔案 (雖然 with 會處理關閉，但明確刪除更保險)
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            # st.write(f"Debug: Removed temp video: {temp_video_path}") # 除錯用
        if temp_gif_path and os.path.exists(temp_gif_path):
            # 讓使用者下載完再刪除可能更好，或者在下次轉換前刪除
            # 這裡暫時保留，讓下載按鈕能運作
            # os.remove(temp_gif_path) # 如果確定不需要保留可取消註解此行
            pass


else:
    st.info("請先上傳一個影片檔案。")

st.write("---")
st.markdown("由程式夥伴協助建立 ❤️")