import sys
import subprocess
import threading
import os
import time
import json
from datetime import datetime
import streamlit as st
from streamlit.components.v1 import html
from typing import Dict, List, Optional

# Konfigurasi halaman
st.set_page_config(
    page_title="StreamFlow - Multi Streaming",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS untuk styling
st.markdown("""
<style>
    /* Reset dan variabel warna */
    :root {
        --primary: #4f46e5;
        --primary-dark: #4338ca;
        --danger: #dc2626;
        --success: #059669;
        --warning: #d97706;
        --dark-bg: #0f172a;
        --card-bg: #1e293b;
        --card-border: #334155;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --live-red: #ef4444;
        --gradient-purple: linear-gradient(135deg, #8b5cf6, #4f46e5);
    }
    
    /* Header styling */
    .main-title {
        text-align: center;
        margin-bottom: 0.5rem;
        background: linear-gradient(90deg, #4f46e5, #8b5cf6, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 900;
        letter-spacing: -1px;
    }
    
    .subtitle {
        text-align: center;
        color: var(--text-secondary);
        font-size: 1.2rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Card styling untuk setiap stream */
    .stream-card {
        background: var(--card-bg);
        border-radius: 16px;
        border: 1px solid var(--card-border);
        padding: 24px;
        margin-bottom: 24px;
        position: relative;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    
    .stream-card:hover {
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        transform: translateY(-2px);
    }
    
    .stream-card.live {
        border-left: 6px solid var(--live-red);
    }
    
    .stream-number {
        position: absolute;
        top: -12px;
        left: 24px;
        background: var(--gradient-purple);
        color: white;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 1.2rem;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    }
    
    .stream-title {
        color: var(--text-primary);
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 8px;
        margin-left: 40px;
    }
    
    .stream-subtitle {
        color: var(--text-secondary);
        font-size: 1rem;
        margin-bottom: 16px;
        margin-left: 40px;
    }
    
    /* Video info section */
    .video-info {
        background: rgba(15, 23, 42, 0.5);
        border-radius: 10px;
        padding: 16px;
        margin: 16px 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .duration {
        background: var(--primary);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .loop-badge {
        background: var(--success);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    /* RTMP info box */
    .rtmp-box {
        background: rgba(15, 23, 42, 0.5);
        border-radius: 10px;
        padding: 12px 16px;
        margin: 12px 0;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 0.9rem;
        color: #60a5fa;
        border-left: 4px solid var(--primary);
    }
    
    /* Settings table */
    .settings-table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        border-radius: 10px;
        overflow: hidden;
        background: rgba(15, 23, 42, 0.5);
    }
    
    .settings-table th {
        background: var(--primary-dark);
        color: white;
        padding: 12px;
        font-weight: 600;
        text-align: center;
    }
    
    .settings-table td {
        padding: 12px;
        text-align: center;
        color: var(--text-primary);
        border-bottom: 1px solid var(--card-border);
    }
    
    /* Button styling */
    .button-group {
        display: flex;
        gap: 12px;
        margin-top: 20px;
    }
    
    .stButton > button {
        border-radius: 10px;
        height: 45px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        flex: 1;
    }
    
    .stop-btn > button {
        background: var(--danger) !important;
        color: white !important;
        border: none !important;
    }
    
    .delete-btn > button {
        background: #475569 !important;
        color: white !important;
        border: none !important;
    }
    
    .live-btn > button {
        background: var(--live-red) !important;
        color: white !important;
        border: none !important;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    /* Live badge */
    .live-badge {
        position: absolute;
        top: 24px;
        right: 24px;
        background: var(--live-red);
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .live-badge::before {
        content: '';
        width: 8px;
        height: 8px;
        background: white;
        border-radius: 50%;
        animation: blink 1.5s infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: var(--text-secondary);
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid var(--card-border);
        font-size: 0.9rem;
    }
    
    /* Hide streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .main-title { font-size: 2.5rem; }
        .button-group { flex-direction: column; }
    }
</style>
""", unsafe_allow_html=True)

class StreamManager:
    """Mengelola multi streaming"""
    
    def __init__(self):
        if 'streams' not in st.session_state:
            st.session_state.streams = {}
        if 'processes' not in st.session_state:
            st.session_state.processes = {}
        if 'stream_logs' not in st.session_state:
            st.session_state.stream_logs = {}
    
    def add_stream(self, stream_id: str, title: str, video_path: str = None):
        """Menambahkan stream baru"""
        st.session_state.streams[stream_id] = {
            'id': stream_id,
            'title': title,
            'video_path': video_path,
            'stream_key': '',
            'status': 'stopped',  # 'stopped', 'starting', 'live', 'error'
            'duration': '0:00',
            'current_time': '0:00',
            'bitrate': 3000,
            'resolution': '1080p',
            'fps': 30,
            'loop_video': True,
            'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2',
            'created_at': datetime.now().isoformat()
        }
        
        st.session_state.stream_logs[stream_id] = []
    
    def update_stream(self, stream_id: str, updates: Dict):
        """Update stream configuration"""
        if stream_id in st.session_state.streams:
            st.session_state.streams[stream_id].update(updates)
    
    def start_stream(self, stream_id: str):
        """Memulai streaming untuk stream tertentu"""
        if stream_id not in st.session_state.streams:
            return False
        
        stream = st.session_state.streams[stream_id]
        
        if not stream['video_path'] or not os.path.exists(stream['video_path']):
            st.error(f"Video untuk {stream['title']} tidak ditemukan!")
            return False
        
        if not stream['stream_key']:
            st.error(f"Stream key untuk {stream['title']} belum diisi!")
            return False
        
        # Update status
        self.update_stream(stream_id, {'status': 'starting'})
        
        # Start streaming in thread
        thread = threading.Thread(
            target=self._run_stream,
            args=(stream_id,),
            daemon=True
        )
        thread.start()
        
        return True
    
    def _run_stream(self, stream_id: str):
        """Jalankan ffmpeg untuk streaming"""
        stream = st.session_state.streams[stream_id]
        
        output_url = f"{stream['rtmp_url']}/{stream['stream_key']}"
        
        cmd = [
            "ffmpeg",
            "-stream_loop", "-1",
            "-re",
            "-i", stream['video_path'],
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", f"{stream['bitrate']}k",
            "-maxrate", f"{stream['bitrate']}k",
            "-bufsize", f"{stream['bitrate'] * 2}k",
            "-pix_fmt", "yuv420p",
            "-g", str(stream['fps'] * 2),
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            output_url
        ]
        
        # Add resolution scaling if needed
        if stream['resolution'] == '720p':
            cmd.insert(-1, "-vf")
            cmd.insert(-1, "scale=1280:720")
        elif stream['resolution'] == '480p':
            cmd.insert(-1, "-vf")
            cmd.insert(-1, "scale=854:480")
        
        try:
            # Update status
            self.update_stream(stream_id, {'status': 'live'})
            
            # Log command
            self._add_log(stream_id, f"🚀 Memulai streaming: {' '.join(cmd[:10])}...")
            
            # Run process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Store process
            st.session_state.processes[stream_id] = process
            
            # Read output
            for line in process.stdout:
                self._add_log(stream_id, line.strip())
                if process.poll() is not None:
                    break
                    
        except Exception as e:
            self._add_log(stream_id, f"❌ Error: {e}")
            self.update_stream(stream_id, {'status': 'error'})
        finally:
            if stream_id in st.session_state.processes:
                del st.session_state.processes[stream_id]
            self.update_stream(stream_id, {'status': 'stopped'})
            self._add_log(stream_id, "⏹️ Streaming dihentikan")
    
    def stop_stream(self, stream_id: str):
        """Menghentikan streaming"""
        if stream_id in st.session_state.processes:
            try:
                st.session_state.processes[stream_id].terminate()
                time.sleep(1)
                if st.session_state.processes[stream_id].poll() is None:
                    st.session_state.processes[stream_id].kill()
            except:
                pass
            
            del st.session_state.processes[stream_id]
        
        self.update_stream(stream_id, {'status': 'stopped'})
        self._add_log(stream_id, "🛑 Streaming dihentikan oleh pengguna")
    
    def delete_stream(self, stream_id: str):
        """Menghapus stream"""
        if stream_id in st.session_state.processes:
            self.stop_stream(stream_id)
        
        if stream_id in st.session_state.streams:
            del st.session_state.streams[stream_id]
        
        if stream_id in st.session_state.stream_logs:
            del st.session_state.stream_logs[stream_id]
    
    def _add_log(self, stream_id: str, message: str):
        """Menambahkan log untuk stream"""
        if stream_id not in st.session_state.stream_logs:
            st.session_state.stream_logs[stream_id] = []
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.stream_logs[stream_id].append(f"[{timestamp}] {message}")
        
        # Keep only last 50 logs
        if len(st.session_state.stream_logs[stream_id]) > 50:
            st.session_state.stream_logs[stream_id] = st.session_state.stream_logs[stream_id][-50:]

def main():
    # Header
    st.markdown('<h1 class="main-title">StreamFlow</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">by Bang Tutorial</p>', unsafe_allow_html=True)
    
    # Initialize stream manager
    manager = StreamManager()
    
    # Initialize default streams if not exists
    default_streams = [
        {
            'id': 'stream1',
            'title': 'Live Musik Anime',
            'duration': '0:14',
            'subtitle': '0:14 / 0:14',
            'video_file': 'anime_music.mp4'  # Default, bisa diganti
        },
        {
            'id': 'stream2',
            'title': 'Live Music Lofi',
            'duration': '2:30',
            'subtitle': 'Bintang 17 di Maret',
            'video_file': 'lofi_music.mp4'
        },
        {
            'id': 'stream3',
            'title': 'Live Suara Hujan & Petir',
            'duration': '1:23',
            'subtitle': '1:23 / 1:23',
            'video_file': 'rain_thunder.mp4'
        }
    ]
    
    for stream_data in default_streams:
        if stream_data['id'] not in st.session_state.streams:
            manager.add_stream(
                stream_data['id'],
                stream_data['title'],
                stream_data['video_file'] if os.path.exists(stream_data['video_file']) else None
            )
            manager.update_stream(stream_data['id'], {
                'duration': stream_data['duration'],
                'current_time': stream_data['duration'],
                'subtitle': stream_data['subtitle']
            })
    
    # Main container
    main_container = st.container()
    
    with main_container:
        # Display all streams
        for stream_id in list(st.session_state.streams.keys()):
            stream = st.session_state.streams[stream_id]
            
            # Determine card class
            card_class = "stream-card"
            if stream['status'] == 'live':
                card_class += " live"
            
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            # Stream number
            stream_num = list(st.session_state.streams.keys()).index(stream_id) + 1
            st.markdown(f'<div class="stream-number">{stream_num}</div>', unsafe_allow_html=True)
            
            # Stream title
            st.markdown(f'<div class="stream-title">{stream["title"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stream-subtitle">{stream.get("subtitle", "")}</div>', unsafe_allow_html=True)
            
            # Live badge if streaming
            if stream['status'] == 'live':
                st.markdown('<div class="live-badge">LIVE</div>', unsafe_allow_html=True)
            
            # Video info section
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown(f'<div class="duration">{stream["duration"]}</div>', unsafe_allow_html=True)
            
            with col2:
                if stream.get('loop_video', True):
                    st.markdown('<div class="loop-badge">Loop Video</div>', unsafe_allow_html=True)
            
            # RTMP URL
            st.markdown(f'<div class="rtmp-box">{stream["rtmp_url"]}</div>', unsafe_allow_html=True)
            
            # Stream settings table
            st.markdown("""
            <table class="settings-table">
                <thead>
                    <tr>
                        <th>Bitrate (kbps)</th>
                        <th>Resolusi</th>
                        <th>FPS</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{bitrate}</td>
                        <td>{resolution}</td>
                        <td>{fps}</td>
                    </tr>
                </tbody>
            </table>
            """.format(
                bitrate=stream['bitrate'],
                resolution=stream['resolution'],
                fps=stream['fps']
            ), unsafe_allow_html=True)
            
            # Stream configuration
            with st.expander("⚙️ Konfigurasi Stream", expanded=False):
                config_col1, config_col2 = st.columns(2)
                
                with config_col1:
                    # Video selection
                    video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv'))]
                    
                    if video_files:
                        selected_video = st.selectbox(
                            "Pilih Video",
                            video_files,
                            index=video_files.index(stream['video_path']) if stream['video_path'] in video_files else 0,
                            key=f"video_select_{stream_id}"
                        )
                        if selected_video != stream['video_path']:
                            manager.update_stream(stream_id, {'video_path': selected_video})
                    
                    # Upload new video
                    uploaded_file = st.file_uploader(
                        "Upload Video Baru",
                        type=['mp4', 'mov', 'avi', 'mkv', 'flv'],
                        key=f"upload_{stream_id}"
                    )
                    
                    if uploaded_file:
                        # Save uploaded file
                        with open(uploaded_file.name, "wb") as f:
                            f.write(uploaded_file.read())
                        manager.update_stream(stream_id, {'video_path': uploaded_file.name})
                        st.success("✅ Video berhasil diupload!")
                
                with config_col2:
                    # Stream key input
                    stream_key = st.text_input(
                        "YouTube Stream Key",
                        value=stream['stream_key'],
                        type="password",
                        key=f"key_{stream_id}"
                    )
                    if stream_key != stream['stream_key']:
                        manager.update_stream(stream_id, {'stream_key': stream_key})
                    
                    # Streaming settings
                    bitrate = st.selectbox(
                        "Bitrate",
                        [1500, 2500, 3000, 4000, 5000],
                        index=[1500, 2500, 3000, 4000, 5000].index(stream['bitrate']) if stream['bitrate'] in [1500, 2500, 3000, 4000, 5000] else 2,
                        key=f"bitrate_{stream_id}"
                    )
                    if bitrate != stream['bitrate']:
                        manager.update_stream(stream_id, {'bitrate': bitrate})
                    
                    resolution = st.selectbox(
                        "Resolusi",
                        ['480p', '720p', '1080p'],
                        index=['480p', '720p', '1080p'].index(stream['resolution']) if stream['resolution'] in ['480p', '720p', '1080p'] else 2,
                        key=f"res_{stream_id}"
                    )
                    if resolution != stream['resolution']:
                        manager.update_stream(stream_id, {'resolution': resolution})
            
            # Button group
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⏹️ Stop", key=f"stop_{stream_id}", use_container_width=True):
                    manager.stop_stream(stream_id)
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Hapus Video", key=f"delete_{stream_id}", use_container_width=True):
                    if stream['video_path'] and os.path.exists(stream['video_path']):
                        try:
                            os.remove(stream['video_path'])
                            manager.update_stream(stream_id, {'video_path': None})
                            st.success("Video dihapus!")
                            time.sleep(1)
                            st.rerun()
                        except:
                            st.error("Gagal menghapus video!")
            
            with col3:
                if stream['status'] != 'live':
                    if st.button("▶️ LIVE", key=f"live_{stream_id}", use_container_width=True):
                        if manager.start_stream(stream_id):
                            st.success(f"Streaming {stream['title']} dimulai!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.markdown('<div class="live-badge" style="position: static; margin: auto;">LIVE</div>', unsafe_allow_html=True)
            
            # Stream logs
            with st.expander("📋 Log Streaming", expanded=False):
                if stream_id in st.session_state.stream_logs:
                    log_text = "\n".join(st.session_state.stream_logs[stream_id][-20:])
                    st.text_area("", value=log_text, height=150, key=f"log_{stream_id}", label_visibility="collapsed")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")
    
    # Add new stream button
    if st.button("➕ Tambah Stream Baru", use_container_width=True):
        new_id = f"stream{len(st.session_state.streams) + 1}"
        manager.add_stream(new_id, f"Stream Baru {len(st.session_state.streams) + 1}")
        st.rerun()
    
    # Footer
    st.markdown('<div class="footer">From Creator for Creator by Bang Tutorial</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()
