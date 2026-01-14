import sys
import subprocess
import threading
import os
import yt_dlp
import requests
import time
import json
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import atexit

# Versi: Streamlit Cloud Fix
st.set_page_config(
    page_title="YouTube Live Streamer",
    page_icon="🎥",
    layout="wide"
)

# Install missing packages
def install_packages():
    try:
        import yt_dlp
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    
    try:
        from streamlit_autorefresh import st_autorefresh
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit-autorefresh"])

install_packages()

# Inisialisasi session state
if 'streaming' not in st.session_state:
    st.session_state.streaming = False
if 'ffmpeg_process' not in st.session_state:
    st.session_state.ffmpeg_process = None
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'stream_key' not in st.session_state:
    st.session_state.stream_key = ""
if 'youtube_url' not in st.session_state:
    st.session_state.youtube_url = ""

def log_message(msg):
    """Simpan log"""
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {msg}"
    st.session_state.logs.append(log_entry)
    print(log_entry)  # Juga print ke console

def extract_hls_url(youtube_url):
    """Extract HLS URL dari YouTube"""
    try:
        log_message(f"🔍 Mengekstrak HLS dari: {youtube_url}")
        
        ydl_opts = {
            'format': 'best[ext=m3u8]/best',
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            # Cari URL HLS
            if 'url' in info and 'm3u8' in info['url']:
                return info['url']
            
            for fmt in info.get('formats', []):
                url = fmt.get('url', '')
                if url and 'm3u8' in url:
                    return url
            
        return None
    except Exception as e:
        log_message(f"❌ Error ekstraksi: {str(e)}")
        return None

def start_streaming_thread(youtube_url, stream_key, is_shorts):
    """Thread untuk memulai streaming"""
    try:
        log_message("🔄 Memulai proses streaming...")
        
        # Extract HLS URL
        hls_url = extract_hls_url(youtube_url)
        if not hls_url:
            st.error("❌ Gagal mendapatkan link HLS")
            st.session_state.streaming = False
            return
        
        log_message(f"✅ HLS URL ditemukan: {hls_url[:80]}...")
        
        # Persiapan output URL
        output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
        
        # Pilih scale filter
        if is_shorts:
            scale = "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2"
        else:
            scale = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-re',
            '-i', hls_url,
            '-vf', scale,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-b:v', '2000k',
            '-maxrate', '2000k',
            '-bufsize', '4000k',
            '-g', '50',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100',
            '-f', 'flv',
            output_url
        ]
        
        log_message(f"🚀 Menjalankan FFmpeg: {' '.join(cmd[:6])}...")
        
        # Jalankan FFmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        st.session_state.ffmpeg_process = process
        st.session_state.streaming = True
        
        # Baca output
        for line in iter(process.stdout.readline, ''):
            if line:
                log_message(f"FFmpeg: {line.strip()}")
        
        process.wait()
        return_code = process.returncode
        
        log_message(f"FFmpeg exited with code: {return_code}")
        
        if return_code == 0:
            log_message("✅ Streaming selesai")
        else:
            log_message("⚠️ Streaming terhenti")
            
        st.session_state.streaming = False
        st.session_state.ffmpeg_process = None
        
    except Exception as e:
        log_message(f"❌ Error dalam thread: {str(e)}")
        st.session_state.streaming = False
        st.session_state.ffmpeg_process = None

def stop_streaming():
    """Hentikan streaming"""
    if st.session_state.ffmpeg_process:
        try:
            st.session_state.ffmpeg_process.terminate()
            time.sleep(1)
            if st.session_state.ffmpeg_process.poll() is None:
                st.session_state.ffmpeg_process.kill()
            log_message("🛑 Streaming dihentikan")
        except:
            pass
    
    st.session_state.streaming = False
    st.session_state.ffmpeg_process = None

# Cleanup saat app berhenti
def cleanup():
    if st.session_state.ffmpeg_process:
        stop_streaming()

atexit.register(cleanup)

def main():
    st.title("🎥 YouTube Live Streamer")
    st.markdown("---")
    
    # Auto refresh
    st_autorefresh(interval=3000, key="data_refresh")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Konfigurasi")
        
        # Stream Key
        stream_key = st.text_input(
            "🔑 YouTube Stream Key",
            value="gqz2-2uus-yyhv-srkd-ay8g",
            type="password",
            key="stream_key_input"
        )
        
        st.session_state.stream_key = stream_key
        
        # Mode
        is_shorts = st.checkbox("📱 Mode Shorts (Vertical)", value=False)
        
        st.markdown("---")
        
        # Status
        status = "🔴 LIVE" if st.session_state.streaming else "⏸️ STOPPED"
        color = "red" if st.session_state.streaming else "gray"
        
        st.markdown(f"""
        <div style='background-color:#f0f2f6;padding:10px;border-radius:5px'>
            <h4 style='color:{color};margin:0'>Status: {status}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Info
        st.info("""
        **Cara Penggunaan:**
        1. Masukkan Stream Key dari YouTube Studio
        2. Masukkan URL YouTube Live
        3. Klik START STREAMING
        4. Pantau di YouTube Studio > Live Dashboard
        """)
    
    # Tabs utama
    tab1, tab2 = st.tabs(["📡 Streaming", "📋 Logs"])
    
    with tab1:
        st.header("Streaming Control")
        
        # URL Input
        youtube_url = st.text_input(
            "📺 YouTube Live URL",
            value="https://www.youtube.com/live/uN9pBrS7EaQ",
            placeholder="https://www.youtube.com/live/...",
            key="youtube_url_input"
        )
        
        st.session_state.youtube_url = youtube_url
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_disabled = st.session_state.streaming or not stream_key or not youtube_url
            if st.button("🚀 START STREAMING", 
                        type="primary", 
                        disabled=start_disabled,
                        use_container_width=True):
                
                if not stream_key:
                    st.error("❌ Stream Key harus diisi!")
                elif not youtube_url:
                    st.error("❌ URL YouTube harus diisi!")
                else:
                    # Start streaming dalam thread
                    thread = threading.Thread(
                        target=start_streaming_thread,
                        args=(youtube_url, stream_key, is_shorts),
                        daemon=True
                    )
                    thread.start()
                    
                    st.success("✅ Streaming dimulai! Lihat log untuk progress...")
                    st.balloons()
                    
                    # Auto refresh untuk update status
                    st.rerun()
        
        with col2:
            if st.button("🛑 STOP STREAMING", 
                        type="secondary",
                        disabled=not st.session_state.streaming,
                        use_container_width=True):
                stop_streaming()
                st.warning("⚠️ Menghentikan streaming...")
                st.rerun()
        
        with col3:
            if st.button("🔄 REFRESH", use_container_width=True):
                st.rerun()
        
        # Status box
        st.markdown("---")
        
        if st.session_state.streaming:
            with st.container():
                st.success("""
                ### ✅ STREAMING AKTIF
                
                **Stream sedang berjalan ke YouTube Live**
                
                **URL Streaming:** `rtmp://a.rtmp.youtube.com/live2/******`
                
                **Sumber:** `{youtube_url}`
                
                **Mode:** `{'Shorts (720x1280)' if is_shorts else 'Landscape (1280x720)'}`
                
                **Status:** 🔴 **LIVE NOW**
                """)
                
                # Progress indicator
                progress_bar = st.progress(0)
                for i in range(100):
                    if not st.session_state.streaming:
                        break
                    time.sleep(0.1)
                    progress_bar.progress(i + 1)
                
        else:
            st.info("""
            ### 📝 READY TO STREAM
            
            **Status:** ⏸️ **STOPPED**
            
            **Instruksi:**
            1. Pastikan URL YouTube Live valid
            2. Stream Key sudah diisi
            3. Klik START STREAMING untuk mulai
            """)
        
        # Quick test section
        with st.expander("🔧 Quick Connection Test"):
            if st.button("Test FFmpeg"):
                try:
                    result = subprocess.run(['ffmpeg', '-version'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        st.success("✅ FFmpeg tersedia")
                        st.code(result.stdout[:200])
                    else:
                        st.error("❌ FFmpeg tidak tersedia")
                except:
                    st.error("❌ FFmpeg tidak terinstall")
            
            if st.button("Test HLS Extraction"):
                if youtube_url:
                    with st.spinner("Mengekstrak HLS..."):
                        hls_url = extract_hls_url(youtube_url)
                        if hls_url:
                            st.success("✅ HLS ditemukan")
                            st.code(hls_url[:200] + "...")
                        else:
                            st.error("❌ Gagal ekstrak HLS")
    
    with tab2:
        st.header("Streaming Logs")
        
        # Clear logs button
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("Clear Logs", key="clear_logs"):
                st.session_state.logs = []
                st.rerun()
        
        # Display logs
        log_container = st.container(height=400)
        with log_container:
            for log in st.session_state.logs[-20:]:
                if "❌" in log or "ERROR" in log:
                    st.error(log)
                elif "✅" in log or "SUCCESS" in log:
                    st.success(log)
                elif "⚠️" in log or "WARNING" in log:
                    st.warning(log)
                elif "🚀" in log or "🔍" in log:
                    st.info(log)
                else:
                    st.text(log)
        
        # Log count
        st.caption(f"Total logs: {len(st.session_state.logs)}")

if __name__ == "__main__":
    main()
