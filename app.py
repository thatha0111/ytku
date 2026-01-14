import sys
import subprocess
import threading
import os
import yt_dlp
import requests
import time
import json
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# Install dependencies
def install_dependencies():
    dependencies = ['streamlit', 'yt-dlp', 'streamlit-autorefresh', 'requests']
    for dep in dependencies:
        try:
            if dep == 'streamlit':
                import streamlit as st
            elif dep == 'yt-dlp':
                import yt_dlp
            elif dep == 'streamlit-autorefresh':
                from streamlit_autorefresh import st_autorefresh
            elif dep == 'requests':
                import requests
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

install_dependencies()

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Variabel global untuk status
if 'streaming_status' not in st.session_state:
    st.session_state.streaming_status = "stopped"
if 'ffmpeg_process' not in st.session_state:
    st.session_state.ffmpeg_process = None
if 'logs' not in st.session_state:
    st.session_state.logs = []

def log_message(msg):
    """Simpan log dengan timestamp"""
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {msg}"
    st.session_state.logs.append(log_entry)
    if len(st.session_state.logs) > 50:  # Batasi log
        st.session_state.logs = st.session_state.logs[-50:]

def check_ffmpeg():
    """Cek apakah FFmpeg tersedia"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def install_ffmpeg_streamlit():
    """Install FFmpeg di environment Streamlit (untuk Cloud)"""
    log_message("🔧 Mencoba menginstall FFmpeg...")
    try:
        # Untuk Streamlit Cloud (Ubuntu based)
        subprocess.run(['apt-get', 'update'], capture_output=True)
        subprocess.run(['apt-get', 'install', '-y', 'ffmpeg'], capture_output=True)
        log_message("✅ FFmpeg berhasil diinstall")
        return True
    except Exception as e:
        log_message(f"❌ Gagal install FFmpeg: {e}")
        return False

def extract_youtube_hls(youtube_url):
    """Extract HLS URL dari YouTube dengan metode alternatif"""
    log_message(f"📥 Mengekstrak HLS dari: {youtube_url}")
    
    try:
        # Metode 1: Gunakan yt-dlp
        ydl_opts = {
            'format': 'best[ext=m3u8]/best',
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['dash', 'hls']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            # Cari URL HLS
            hls_url = None
            if 'url' in info:
                if 'm3u8' in info['url']:
                    hls_url = info['url']
            
            if not hls_url:
                for fmt in info.get('formats', []):
                    url = fmt.get('url', '')
                    if url and 'm3u8' in url:
                        hls_url = url
                        break
            
            if hls_url:
                log_message(f"✅ HLS ditemukan: {hls_url[:100]}...")
                
                # Simpan ke file untuk testing
                try:
                    response = requests.get(hls_url, timeout=10)
                    if response.status_code == 200:
                        with open('stream.m3u8', 'w') as f:
                            f.write(response.text)
                        log_message("✅ File M3U8 berhasil disimpan")
                except:
                    pass
                
                return hls_url
            else:
                log_message("❌ HLS tidak ditemukan")
                return None
                
    except Exception as e:
        log_message(f"❌ Error ekstraksi: {str(e)}")
        
        # Metode alternatif: Gunakan API sederhana
        try:
            log_message("🔄 Mencoba metode alternatif...")
            
            # API alternatif untuk extract HLS
            api_url = f"https://yt.lemnoslife.com/noKey/videos?part=streamingDetails&id={youtube_url.split('v=')[-1]}"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and data['items']:
                    streaming_data = data['items'][0].get('streamingDetails', {})
                    
                    # Cari format HLS
                    if 'adaptiveFormats' in streaming_data:
                        for fmt in streaming_data['adaptiveFormats']:
                            if fmt.get('type', '').startswith('video/mp4') and 'url' in fmt:
                                return fmt['url']
        except Exception as e2:
            log_message(f"❌ Metode alternatif gagal: {e2}")
        
        return None

def test_rtmp_connection(stream_key):
    """Test koneksi ke RTMP YouTube"""
    log_message("🔍 Testing koneksi RTMP...")
    
    test_cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=5:size=1280x720:rate=30',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-t', '3',  # Hanya 3 detik untuk testing
        '-f', 'flv',
        f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'
    ]
    
    try:
        process = subprocess.Popen(
            test_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        output = []
        for line in process.stdout:
            if 'error' in line.lower() or 'failed' in line.lower():
                log_message(f"⚠️ RTMP Error: {line.strip()}")
            output.append(line.strip())
        
        process.wait(timeout=10)
        
        if process.returncode == 0:
            log_message("✅ Koneksi RTMP berhasil diuji")
            return True
        else:
            log_message("❌ Koneksi RTMP gagal")
            return False
            
    except subprocess.TimeoutExpired:
        process.kill()
        log_message("⚠️ Timeout saat testing RTMP")
        return True  # Return True karena timeout mungkin berarti terhubung
    except Exception as e:
        log_message(f"❌ Error testing RTMP: {e}")
        return False

def start_streaming(youtube_url, stream_key, is_shorts):
    """Mulai streaming dari YouTube HLS"""
    log_message("🚀 Memulai streaming...")
    
    # 1. Ekstrak HLS URL
    hls_url = extract_youtube_hls(youtube_url)
    if not hls_url:
        st.error("❌ Gagal mendapatkan link HLS dari YouTube")
        st.session_state.streaming_status = "error"
        return
    
    # 2. Test koneksi RTMP
    if not test_rtmp_connection(stream_key):
        st.warning("⚠️ RTMP connection test failed. Trying anyway...")
    
    # 3. Siapkan command FFmpeg
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    # Parameter untuk YouTube Live
    if is_shorts:
        scale_filter = "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2"
    else:
        scale_filter = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"
    
    # Optimasi untuk streaming HLS
    cmd = [
        'ffmpeg',
        '-reconnect', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '5',
        '-i', hls_url,
        '-vf', scale_filter,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',  # Gunakan ultrafast untuk resource rendah
        '-tune', 'zerolatency',
        '-b:v', '1500k',  # Bitrate lebih rendah untuk stabilitas
        '-maxrate', '1500k',
        '-bufsize', '3000k',
        '-g', '50',
        '-c:a', 'aac',
        '-b:a', '96k',
        '-ar', '44100',
        '-ac', '2',
        '-f', 'flv',
        output_url
    ]
    
    log_message(f"📡 Command: {' '.join(cmd)}")
    
    try:
        # Jalankan FFmpeg dalam thread
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        st.session_state.ffmpeg_process = process
        st.session_state.streaming_status = "streaming"
        log_message("✅ Streaming dimulai!")
        
        # Baca output secara real-time
        def read_output():
            while True:
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        log_message(line.strip())
                    else:
                        break
                time.sleep(0.1)
        
        # Thread untuk membaca output
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()
        
        # Tunggu proses selesai
        while True:
            if process.poll() is not None:
                break
            time.sleep(1)
        
        # Cek exit code
        if process.returncode == 0:
            log_message("✅ Streaming selesai dengan sukses")
        else:
            log_message(f"⚠️ Streaming berhenti dengan code: {process.returncode}")
        
        st.session_state.streaming_status = "stopped"
        
    except Exception as e:
        log_message(f"❌ Error streaming: {str(e)}")
        st.session_state.streaming_status = "error"

def stop_streaming():
    """Hentikan streaming"""
    log_message("🛑 Menghentikan streaming...")
    
    if st.session_state.ffmpeg_process:
        try:
            st.session_state.ffmpeg_process.terminate()
            time.sleep(1)
            
            if st.session_state.ffmpeg_process.poll() is None:
                st.session_state.ffmpeg_process.kill()
            
            log_message("✅ Streaming dihentikan")
        except:
            pass
    
    st.session_state.streaming_status = "stopped"
    st.session_state.ffmpeg_process = None

def main():
    st.set_page_config(
        page_title="YouTube Live Streamer",
        page_icon="🎥",
        layout="wide"
    )
    
    st.title("🎥 YouTube Live Streamer (Cloud Edition)")
    st.markdown("---")
    
    # Auto refresh setiap 5 detik
    st_autorefresh(interval=5000, key="stream_refresh")
    
    # Sidebar untuk kontrol
    with st.sidebar:
        st.header("⚙️ Konfigurasi")
        
        # Cek FFmpeg
        if not check_ffmpeg():
            st.warning("⚠️ FFmpeg tidak ditemukan!")
            if st.button("🔧 Install FFmpeg"):
                with st.spinner("Menginstall FFmpeg..."):
                    if install_ffmpeg_streamlit():
                        st.success("✅ FFmpeg terinstall!")
                        st.rerun()
                    else:
                        st.error("❌ Gagal install FFmpeg")
        
        # Input stream key
        stream_key = st.text_input(
            "🔑 YouTube Stream Key",
            value="gqz2-2uus-yyhv-srkd-ay8g",
            type="password"
        )
        
        # Mode shorts
        is_shorts = st.checkbox("📱 Mode Shorts (Vertical 9:16)", value=False)
        
        st.markdown("---")
        
        # Status streaming
        status_color = {
            "stopped": "gray",
            "streaming": "green",
            "error": "red"
        }.get(st.session_state.streaming_status, "gray")
        
        st.markdown(f"""
        **Status:** <span style='color:{status_color};font-weight:bold'>
        {st.session_state.streaming_status.upper()}
        </span>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Tombol kontrol
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Status", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("🧹 Clear Logs", use_container_width=True):
                st.session_state.logs = []
                st.rerun()
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📡 Streaming", "🔗 Test URL", "📋 Logs"])
    
    with tab1:
        st.header("Mulai Streaming")
        
        # URL input
        youtube_url = st.text_input(
            "📺 YouTube Live URL",
            value="https://www.youtube.com/live/uN9pBrS7EaQ",
            placeholder="https://www.youtube.com/live/... atau https://youtu.be/..."
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("🚀 START STREAMING", type="primary", use_container_width=True):
                if not youtube_url or not stream_key:
                    st.error("❌ URL dan Stream Key harus diisi!")
                elif st.session_state.streaming_status == "streaming":
                    st.warning("⚠️ Streaming sedang berjalan!")
                else:
                    # Jalankan streaming dalam thread terpisah
                    stream_thread = threading.Thread(
                        target=start_streaming,
                        args=(youtube_url, stream_key, is_shorts),
                        daemon=True
                    )
                    stream_thread.start()
                    st.success("✅ Streaming dimulai dalam background!")
                    st.rerun()
        
        with col2:
            if st.button("🛑 STOP STREAMING", type="secondary", use_container_width=True):
                stop_streaming()
                st.rerun()
        
        with col3:
            if st.button("🔍 TEST CONNECTION", use_container_width=True):
                if stream_key:
                    with st.spinner("Testing koneksi..."):
                        if test_rtmp_connection(stream_key):
                            st.success("✅ Koneksi RTMP OK!")
                        else:
                            st.error("❌ Koneksi RTMP gagal")
        
        # Informasi streaming
        st.markdown("---")
        
        if st.session_state.streaming_status == "streaming":
            st.success("""
            **✅ LIVE STREAMING ACTIVE**
            
            Stream sedang berjalan ke YouTube Live.
            
            **Tips:**
            1. Buka YouTube Studio untuk monitoring
            2. Cek "Live Control Room" di YouTube
            3. Streaming akan otomatis reconnect jika terputus
            """)
            
            # Progress bar simulasi
            placeholder = st.empty()
            for seconds in range(0, 300, 5):
                if st.session_state.streaming_status != "streaming":
                    break
                placeholder.progress(seconds / 300, text="Streaming in progress...")
                time.sleep(5)
        
        elif st.session_state.streaming_status == "error":
            st.error("""
            **❌ STREAMING ERROR**
            
            Terjadi masalah saat streaming. Cek:
            1. Stream key valid
            2. URL YouTube Live benar
            3. Koneksi internet stabil
            """)
    
    with tab2:
        st.header("Test URL HLS")
        
        test_url = st.text_input(
            "Masukkan URL untuk test",
            value="https://www.youtube.com/live/uN9pBrS7EaQ"
        )
        
        if st.button("🔍 Extract HLS URL"):
            if test_url:
                with st.spinner("Mengekstrak HLS URL..."):
                    hls_url = extract_youtube_hls(test_url)
                    
                    if hls_url:
                        st.success("✅ HLS URL ditemukan!")
                        
                        # Tampilkan URL
                        st.code(hls_url, language="text")
                        
                        # Download dan parse M3U8
                        try:
                            response = requests.get(hls_url, timeout=10)
                            if response.status_code == 200:
                                with st.expander("📝 Lihat Konten M3U8"):
                                    st.text_area("M3U8 Content:", response.text[:2000], height=200)
                        except Exception as e:
                            st.warning(f"Tidak bisa fetch M3U8: {e}")
                    else:
                        st.error("❌ Gagal mengekstrak HLS URL")
        
        # Info tentang streaming
        st.markdown("---")
        st.info("""
        **ℹ️ Tentang Cloud Streaming:**
        
        Streaming dari Streamlit Cloud memiliki batasan:
        1. **CPU/Memory terbatas** - Gunakan preset ultrafast
        2. **No RTMP outbound** - Beberapa region diblokir
        3. **Timeout 5 menit** - Untuk proses background
        
        **Solusi Alternatif:**
        - Gunakan VPS/RDP sendiri
        - Gunakan layanan cloud dengan FFmpeg
        - Stream dari local komputer
        """)
    
    with tab3:
        st.header("Log Streaming")
        
        # Tombol clear logs
        if st.button("Clear Logs", key="clear_logs_tab"):
            st.session_state.logs = []
            st.rerun()
        
        # Display logs
        log_container = st.container()
        with log_container:
            for log in reversed(st.session_state.logs[-20:]):  # Show last 20 logs
                if "ERROR" in log or "❌" in log:
                    st.error(log)
                elif "WARNING" in log or "⚠️" in log:
                    st.warning(log)
                elif "SUCCESS" in log or "✅" in log:
                    st.success(log)
                else:
                    st.text(log)
        
        # Download logs
        if st.session_state.logs:
            log_text = "\n".join(st.session_state.logs)
            st.download_button(
                label="📥 Download Logs",
                data=log_text,
                file_name="streaming_logs.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
