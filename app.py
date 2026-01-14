import sys
import subprocess
import threading
import os
import streamlit as st
from streamlit.components.v1 import html
import time

# Install streamlit jika belum ada
try:
    import streamlit as st
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

# Konfigurasi halaman
st.set_page_config(
    page_title="StreamFlow",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS untuk styling seperti gambar
st.markdown("""
<style>
    /* Warna utama */
    :root {
        --primary-color: #2563eb;
        --secondary-color: #1e40af;
        --dark-bg: #0f172a;
        --card-bg: #1e293b;
        --text-light: #f1f5f9;
        --text-muted: #94a3b8;
    }
    
    /* Header styling */
    .main-header {
        color: var(--text-light);
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0;
        text-align: center;
        background: linear-gradient(90deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .sub-header {
        color: var(--text-muted);
        text-align: center;
        font-size: 1.2rem;
        margin-top: 0;
        margin-bottom: 2rem;
    }
    
    /* Card styling */
    .stream-card {
        background-color: var(--card-bg);
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 20px;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
    }
    
    .video-preview {
        background-color: #0f172a;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        border: 2px dashed #475569;
        min-height: 250px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    /* Label styling */
    .section-label {
        color: var(--text-light);
        font-size: 1.8rem;
        font-weight: 600;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .section-label span {
        background: linear-gradient(90deg, #2563eb, #7c3aed);
        color: white;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 50px;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }
    
    .start-button {
        background: linear-gradient(90deg, #2563eb, #1e40af) !important;
        color: white !important;
        border: none !important;
    }
    
    .delete-button {
        background: linear-gradient(90deg, #dc2626, #b91c1c) !important;
        color: white !important;
        border: none !important;
    }
    
    /* Table styling */
    .stream-table {
        width: 100%;
        border-collapse: collapse;
        border-radius: 10px;
        overflow: hidden;
    }
    
    .stream-table th {
        background-color: #2563eb;
        color: white;
        padding: 15px;
        text-align: center;
        font-weight: 600;
    }
    
    .stream-table td {
        background-color: #1e293b;
        color: var(--text-light);
        padding: 15px;
        text-align: center;
        border-bottom: 1px solid #334155;
    }
    
    /* Stream info box */
    .stream-info {
        background-color: #0f172a;
        border-radius: 10px;
        padding: 15px;
        font-family: monospace;
        color: #60a5fa;
        border-left: 4px solid #2563eb;
        margin: 15px 0;
    }
    
    /* Hide streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Container styling */
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)

def run_ffmpeg(video_path, stream_key, log_callback):
    """Menjalankan proses ffmpeg untuk streaming ke YouTube"""
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-re",
        "-i", video_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", "3000k",
        "-maxrate", "3000k",
        "-bufsize", "6000k",
        "-pix_fmt", "yuv420p",
        "-g", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        output_url
    ]
    
    log_callback(f"🚀 Memulai streaming dengan bitrate 3000kbps, 1080p, 30fps")
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Baca output secara real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                log_callback(output.strip())
        
    except Exception as e:
        log_callback(f"❌ Error: {e}")
    finally:
        log_callback("⏹️ Streaming dihentikan")

def main():
    # Header utama
    st.markdown('<h1 class="main-header">StreamFlow</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">by Bang Thanak</p>', unsafe_allow_html=True)
    
    # Kontainer utama
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Bagian 1 - Anime (Video)
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="section-label"><span>1</span> Anime</div>', unsafe_allow_html=True)
        
        # Video preview card
        st.markdown('<div class="stream-card">', unsafe_allow_html=True)
        st.markdown('<div class="video-preview">', unsafe_allow_html=True)
        
        # List video yang tersedia
        video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv'))]
        
        if video_files:
            selected_video = st.selectbox(
                "Pilih video untuk streaming",
                video_files,
                key="video_select",
                label_visibility="collapsed"
            )
            
            # Tampilkan video yang dipilih
            if selected_video:
                video_path = selected_video
                st.video(video_path)
                st.markdown("**Loop Video**")
        else:
            st.info("📁 Tidak ada video ditemukan di direktori")
            st.info("Upload video untuk memulai streaming")
            video_path = None
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Bagian kontrol streaming
        st.markdown('<div class="stream-card">', unsafe_allow_html=True)
        
        # RTMP URL info
        st.markdown("**RTMP URL**")
        st.markdown('<div class="stream-info">rtmp://a.rtmp.youtube.com/live2</div>', unsafe_allow_html=True)
        
        # Input Stream Key
        stream_key = st.text_input(
            "Stream Key",
            type="password",
            placeholder="Masukkan stream key YouTube",
            key="stream_key"
        )
        
        # Tabel setting streaming
        st.markdown("**Stream Settings**")
        st.markdown("""
        <table class="stream-table">
            <thead>
                <tr>
                    <th>Bitrate (kbps)</th>
                    <th>Resolusi</th>
                    <th>FPS</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>3000</td>
                    <td>1080p</td>
                    <td>30fps</td>
                </tr>
            </tbody>
        </table>
        """, unsafe_allow_html=True)
        
        # Tombol Start dan Hapus Video
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🚀 Start", key="start_stream", use_container_width=True):
                if not video_path:
                    st.error("❌ Pilih video terlebih dahulu!")
                elif not stream_key:
                    st.error("❌ Masukkan Stream Key!")
                else:
                    # Inisialisasi thread streaming
                    if 'stream_thread' not in st.session_state:
                        st.session_state.stream_thread = None
                    
                    if st.session_state.stream_thread is None or not st.session_state.stream_thread.is_alive():
                        # Fungsi untuk update log
                        def update_log(msg):
                            if 'stream_logs' not in st.session_state:
                                st.session_state.stream_logs = []
                            st.session_state.stream_logs.append(f"{time.strftime('%H:%M:%S')} - {msg}")
                        
                        # Mulai streaming di thread terpisah
                        thread = threading.Thread(
                            target=run_ffmpeg,
                            args=(video_path, stream_key, update_log),
                            daemon=True
                        )
                        thread.start()
                        st.session_state.stream_thread = thread
                        st.session_state.streaming = True
                        st.success("✅ Streaming dimulai!")
        
        with col_btn2:
            if st.button("🗑️ Hapus Video", key="delete_video", use_container_width=True):
                if video_path and os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                        st.success(f"✅ Video '{video_path}' dihapus!")
                        st.rerun()
                    except:
                        st.error("❌ Gagal menghapus video")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Log streaming
    st.markdown('<div class="stream-card">', unsafe_allow_html=True)
    st.markdown("**Stream Log**")
    
    log_container = st.empty()
    
    # Update log secara real-time
    if 'stream_logs' in st.session_state:
        log_text = "\n".join(st.session_state.stream_logs[-20:])  # Tampilkan 20 log terakhir
        log_container.text_area("", value=log_text, height=200, label_visibility="collapsed")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Tombol stop streaming
    if st.session_state.get('streaming', False):
        if st.button("⏹️ Stop Streaming", key="stop_stream", use_container_width=True):
            # Hentikan proses ffmpeg
            os.system("pkill -f ffmpeg")
            st.session_state.streaming = False
            
            if 'stream_logs' in st.session_state:
                st.session_state.stream_logs.append(f"{time.strftime('%H:%M:%S')} - ⏹️ Streaming dihentikan oleh pengguna")
            
            st.success("✅ Streaming dihentikan!")
            time.sleep(1)
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    # Inisialisasi session state
    if 'streaming' not in st.session_state:
        st.session_state.streaming = False
    if 'stream_logs' not in st.session_state:
        st.session_state.stream_logs = []
    
    main()
