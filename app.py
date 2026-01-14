import sys
import subprocess
import threading
import os
import yt_dlp
import streamlit.components.v1 as components

# Install dependencies jika belum ada
try:
    import streamlit as st
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

# Install yt-dlp jika belum ada
try:
    import yt_dlp
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp


def extract_hls_url(youtube_url):
    """Ekstrak link HLS/m3u8 dari URL YouTube"""
    ydl_opts = {
        'format': 'best[ext=m3u8]/best',  # Prioritaskan format HLS
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            # Cari URL HLS
            if 'url' in info:
                if 'm3u8' in info['url']:
                    return info['url']
            
            # Cari di format
            for fmt in info.get('formats', []):
                if 'm3u8' in fmt.get('url', ''):
                    return fmt['url']
            
            return None
            
    except Exception as e:
        print(f"Error extracting HLS: {e}")
        return None


def run_ffmpeg_hls(hls_url, stream_key, is_shorts, log_callback):
    """Menjalankan ffmpeg dengan input HLS/m3u8"""
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale_filter = "scale=720:1280" if is_shorts else "scale=1280:720"
    
    # Parameter untuk HLS input
    cmd = [
        "ffmpeg",
        "-re",                            # Real-time mode
        "-i", hls_url,                    # Input HLS URL
        "-vf", scale_filter,              # Scaling
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-b:v", "2500k",
        "-maxrate", "2500k",
        "-bufsize", "5000k",
        "-g", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        "-flvflags", "no_duration_filesize",
        output_url
    ]
    
    log_callback(f"Menjalankan HLS streaming: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if line.strip():  # Hanya tampilkan line yang tidak kosong
                log_callback(line.strip())
        process.wait()
    except Exception as e:
        log_callback(f"Error: {e}")
    finally:
        log_callback("HLS streaming selesai atau dihentikan.")


def run_ffmpeg_file(video_path, stream_key, is_shorts, log_callback):
    """Menjalankan ffmpeg dengan input file lokal"""
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale_filter = "scale=720:1280" if is_shorts else "scale=1280:720"

    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",              # Loop tanpa henti
        "-fflags", "+genpts",             # Generate timestamp baru
        "-re",                            # Real-time mode
        "-i", video_path,                 # Input file
        "-vf", scale_filter,              # Scaling
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-b:v", "2500k",
        "-maxrate", "2500k",
        "-bufsize", "5000k",
        "-g", "60",
        "-keyint_min", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        "-flvflags", "no_duration_filesize",
        "-use_wallclock_as_timestamps", "1",
        output_url
    ]

    log_callback(f"Menjalankan file streaming: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if line.strip():
                log_callback(line.strip())
        process.wait()
    except Exception as e:
        log_callback(f"Error: {e}")
    finally:
        log_callback("File streaming selesai atau dihentikan.")


def main():
    st.set_page_config(page_title="Streaming YouTube Live", page_icon="🎥", layout="wide")

    # ✅ Naikkan limit upload
    st.config.set_option("server.maxUploadSize", 1000)

    st.title("🎥 Live Streaming ke YouTube")
    
    # Tab untuk pilihan sumber
    tab1, tab2, tab3 = st.tabs(["📁 File Lokal", "🔗 HLS/YouTube", "ℹ️ Info & Bantuan"])
    
    with tab1:
        st.subheader("Streaming dari File Lokal")
        
        # List video yang tersedia
        video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.flv', '.mkv', '.mov'))]
        
        if video_files:
            selected_video = st.selectbox("Pilih video yang ada", video_files)
            st.write(f"✅ Video terpilih: `{selected_video}`")
            video_path = selected_video
        else:
            video_path = None
            st.info("📝 Tidak ada video di folder saat ini")
        
        uploaded_file = st.file_uploader(
            "Atau upload video baru (format: mp4/flv/mkv/mov - codec H264/AAC)", 
            type=['mp4', 'flv', 'mkv', 'mov']
        )

        if uploaded_file:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.read())
            st.success(f"✅ Video berhasil diupload: `{uploaded_file.name}`")
            video_path = uploaded_file.name
    
    with tab2:
        st.subheader("Streaming dari URL HLS/YouTube")
        
        url_type = st.radio(
            "Pilih jenis URL:",
            ["URL HLS langsung", "URL YouTube"],
            horizontal=True
        )
        
        if url_type == "URL HLS langsung":
            hls_url = st.text_input(
                "Masukkan URL HLS/M3U8:",
                placeholder="https://example.com/stream.m3u8",
                help="Masukkan link HLS langsung (format .m3u8)"
            )
            
            if hls_url:
                st.code(hls_url, language="text")
                
                # Validasi URL HLS
                if not hls_url.lower().endswith('.m3u8') and 'm3u8' not in hls_url.lower():
                    st.warning("⚠️ URL tidak mengandung 'm3u8'. Pastikan ini adalah link HLS yang valid.")
                
                st.info("ℹ️ Mode HLS akan menggunakan real-time streaming tanpa loop.")
        
        else:  # URL YouTube
            youtube_url = st.text_input(
                "Masukkan URL YouTube:",
                placeholder="https://www.youtube.com/watch?v=... atau https://youtu.be/...",
                help="Masukkan link YouTube biasa atau live stream"
            )
            
            if youtube_url:
                hls_url = None
                with st.spinner("🔄 Mengekstrak link HLS dari YouTube..."):
                    hls_url = extract_hls_url(youtube_url)
                    
                if hls_url:
                    st.success("✅ Link HLS berhasil diekstrak!")
                    st.code(hls_url, language="text")
                    
                    # Tampilkan preview info
                    with st.expander("🔍 Detail Link HLS"):
                        st.text_area("URL M3U8:", hls_url, height=100)
                        if 'googlevideo.com' in hls_url:
                            st.info("✅ Link YouTube HLS terdeteksi")
                else:
                    st.error("❌ Gagal mengekstrak link HLS. Pastikan URL valid dan video tersedia.")
    
    with tab3:
        st.subheader("ℹ️ Panduan Penggunaan")
        
        st.markdown("""
        ### 🎯 Cara Menggunakan:
        1. **File Lokal Tab**: Upload atau pilih video untuk di-loop
        2. **HLS/YouTube Tab**: 
           - Masukkan URL HLS langsung (.m3u8)
           - Atau URL YouTube (live/video biasa)
        3. **Masukkan Stream Key** YouTube
        4. **Pilih mode** (Normal/Shorts)
        5. **Klik "🚀 Jalankan Streaming"**
        
        ### 🔗 Contoh URL:
        - **YouTube**: `https://www.youtube.com/watch?v=...`
        - **YouTube Live**: `https://www.youtube.com/live/...`
        - **HLS langsung**: `https://example.com/stream.m3u8`
        
        ### ⚙️ Tips:
        - Untuk live stream, gunakan mode HLS
        - Untuk video berulang, gunakan file lokal
        - Pastikan koneksi internet stabil
        - Stream key bisa didapat dari YouTube Studio > Live Streaming
        """)
    
    # Bagian iklan sponsor (opsional)
    show_ads = st.checkbox("Tampilkan Iklan", value=False)
    if show_ads:
        st.subheader("Iklan Sponsor")
        components.html(
            """
            <div style="background:#f0f2f6;padding:20px;border-radius:10px;text-align:center">
                <p style="color:#888">Iklan akan muncul di sini</p>
            </div>
            """,
            height=100
        )
    
    # Input stream key dan mode (diluar tab)
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        stream_key = st.text_input("🔑 YouTube Stream Key", type="password")
    with col2:
        is_shorts = st.checkbox("📱 Mode Shorts (720x1280)", value=False)
    
    # Status dan log
    log_placeholder = st.empty()
    logs = []
    streaming = st.session_state.get('streaming', False)
    
    def log_callback(msg):
        logs.append(msg)
        try:
            # Tampilkan hanya 15 log terakhir
            log_placeholder.text_area(
                "📋 Log Streaming",
                "\n".join(logs[-15:]),
                height=200,
                key="log_area"
            )
        except:
            print(msg)
    
    if 'ffmpeg_thread' not in st.session_state:
        st.session_state['ffmpeg_thread'] = None
    
    # Tombol aksi
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Jalankan Streaming", type="primary", use_container_width=True):
            # Validasi input
            if not stream_key:
                st.error("❌ Stream key harus diisi!")
                st.stop()
            
            # Tentukan sumber streaming
            if 'hls_url' in locals() and hls_url:
                # Streaming dari HLS
                if not hls_url:
                    st.error("❌ URL HLS tidak valid!")
                    st.stop()
                
                st.session_state['streaming'] = True
                st.session_state['ffmpeg_thread'] = threading.Thread(
                    target=run_ffmpeg_hls,
                    args=(hls_url, stream_key, is_shorts, log_callback),
                    daemon=True
                )
                st.session_state['ffmpeg_thread'].start()
                st.success(f"✅ Streaming HLS dimulai!")
                st.balloons()
                
            elif 'video_path' in locals() and video_path:
                # Streaming dari file lokal
                if not os.path.exists(video_path):
                    st.error(f"❌ File {video_path} tidak ditemukan!")
                    st.stop()
                
                st.session_state['streaming'] = True
                st.session_state['ffmpeg_thread'] = threading.Thread(
                    target=run_ffmpeg_file,
                    args=(video_path, stream_key, is_shorts, log_callback),
                    daemon=True
                )
                st.session_state['ffmpeg_thread'].start()
                st.success(f"✅ Streaming file {video_path} dimulai!")
                st.balloons()
                
            else:
                st.error("❌ Pilih sumber streaming terlebih dahulu!")
    
    with col2:
        if st.button("🛑 Stop Streaming", type="secondary", use_container_width=True):
            st.session_state['streaming'] = False
            # Hentikan semua proses ffmpeg
            os.system("pkill -f ffmpeg 2>/dev/null || taskkill /f /im ffmpeg.exe 2>/dev/null")
            log_callback("⚠️ Streaming dihentikan!")
            st.warning("⚠️ Streaming dihentikan!")
            st.rerun()
    
    with col3:
        if st.button("🧹 Hapus Log", use_container_width=True):
            logs.clear()
            log_placeholder.empty()
            st.rerun()
    
    # Tampilkan status streaming
    if st.session_state.get('streaming', False):
        st.info("🔴 **Sedang streaming...**")
    else:
        st.info("⏸️ **Streaming siap**")
    
    # Tampilkan log
    if logs:
        log_placeholder.text_area(
            "📋 Log Streaming",
            "\n".join(logs[-15:]),
            height=200,
            key="log_area"
        )
    
    # Footer
    st.divider()
    st.caption("💡 **Tips**: Gunakan Chrome/Firefox untuk hasil terbaik. Pastikan FFmpeg terinstall di sistem.")


if __name__ == '__main__':
    # Cek FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
    except FileNotFoundError:
        st.error("⚠️ FFmpeg tidak ditemukan! Silakan install FFmpeg terlebih dahulu.")
        st.stop()
    
    main()
