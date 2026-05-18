import streamlit as st
import cv2
import yaml
import time
import sys
sys.path.append(".") 
from model.hand_detector import HandDetector
from model.gesture_classifier import GestureClassifier
from utils.tts_engine import TTSEngine

# Page configuration
st.set_page_config(
    page_title="Signify - ISL Translator",
    page_icon="🤟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #2E86AB;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .prediction-box {
        background-color: #f0f8ff;
        border-left: 5px solid #2E86AB;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .confidence-text {
        color: #28a745;
        font-weight: bold;
    }
    .stats-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Load configuration
@st.cache_resource
def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

# Initialize components
@st.cache_resource
def initialize_components(config):
    detector = HandDetector(
        max_hands=config['mediapipe']['max_num_hands'],
        detection_confidence=config['mediapipe']['min_detection_confidence'],
        tracking_confidence=config['mediapipe']['min_tracking_confidence']
    )
    classifier = GestureClassifier(
        dictionary_path=config['paths']['dictionary_path'],
        sequence_length=config['gesture']['sequence_length']
    )
    tts_engine = TTSEngine(default_language=config['tts']['default_language'])
    return detector, classifier, tts_engine

# Main app
def main():
    config = load_config()
    detector, classifier, tts_engine = initialize_components(config)
    
    # Header
    st.markdown('<h1 class="main-header">🤟 Signify</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time Indian Sign Language to Text Translator</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/sign-language.png", width=80)
        st.title("⚙️ Settings")
        
        # Language selection
        st.subheader("Output Language")
        languages = {lang['code']: lang['name'] for lang in config['languages']}
        selected_language = st.selectbox(
            "Select Translation Language",
            options=list(languages.keys()),
            format_func=lambda x: languages[x]
        )
        
        # TTS settings
        st.subheader("Audio Settings")
        enable_tts = st.checkbox("Enable Text-to-Speech", value=True)
        
        # Display settings
        st.subheader("Display Settings")
        show_landmarks = st.checkbox("Show Hand Landmarks", value=True)
        show_confidence = st.checkbox("Show Confidence Score", value=True)
        
        # Info section
        st.divider()
        st.info("📚 **Available Signs:** " + str(len(classifier.get_available_signs())))
        
        # Instructions
        with st.expander("📖 How to Use"):
            st.markdown("""
            1. Click **Start Camera** to begin
            2. Show ISL signs to the camera
            3. Wait for stable detection
            4. View translated text and hear audio
            5. Click **Reset** to start new sign
            """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📹 Live Camera Feed")
        
        # Camera controls
        start_button = st.button("🎥 Start Camera", type="primary")
        stop_button = st.button("⏹️ Stop Camera")
        
        # Placeholder for video
        video_placeholder = st.empty()
        
    with col2:
        st.subheader("💬 Translation Output")
        
        # Current prediction display
        prediction_container = st.container()
        with prediction_container:
            st.markdown('<div class="prediction-box">', unsafe_allow_html=True)
            detected_text = st.empty()
            translated_text = st.empty()
            confidence_display = st.empty()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Reset button
        if st.button("🔄 Reset Current Sign"):
            classifier.reset_prediction()
            st.success("Prediction reset!")
        
        # Translation history
        st.subheader("📝 Translation History")
        if 'translation_history' not in st.session_state:
            st.session_state.translation_history = []
        
        history_container = st.container()
        with history_container:
            if st.session_state.translation_history:
                for i, item in enumerate(reversed(st.session_state.translation_history[-5:])):
                    st.text(f"{i+1}. {item}")
            else:
                st.info("No translations yet...")
    
    # Camera processing
    if start_button:
        st.session_state.camera_active = True
    if stop_button:
        st.session_state.camera_active = False
    
    if 'camera_active' not in st.session_state:
        st.session_state.camera_active = False
    
    if st.session_state.camera_active:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['ui']['camera_width'])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['ui']['camera_height'])
        
        last_spoken_text = ""
        
        while st.session_state.camera_active:
            ret, frame = cap.read()
            if not ret:
                st.error("Failed to access camera")
                break
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Detect hands
            frame, results = detector.find_hands(frame, draw=show_landmarks)
            
            # Get landmarks and classify
            landmark_list = detector.get_position(frame, results)
            
            current_gesture = None
            confidence = 0.0
            
            if landmark_list:
                fingers_up = detector.is_finger_up(landmark_list)
                current_gesture, confidence = classifier.classify_gesture_basic(
                    landmark_list, fingers_up
                )
                
                # Get stable prediction
                stable_gesture, stable_confidence = classifier.get_stable_prediction(
                    current_gesture, confidence, 
                    threshold=config['gesture']['confidence_threshold']
                )
                
                if stable_gesture:
                    # Translate
                    translated = classifier.translate_gesture(stable_gesture, selected_language)
                    
                    # Update display
                    detected_text.markdown(f"**Detected:** {stable_gesture.upper()}")
                    translated_text.markdown(f"**Translation:** {translated}")
                    
                    if show_confidence:
                        confidence_display.markdown(
                            f'<span class="confidence-text">Confidence: {stable_confidence:.2%}</span>', 
                            unsafe_allow_html=True
                        )
                    
                    # TTS
                    if enable_tts and translated and translated != last_spoken_text:
                        audio_path = tts_engine.text_to_speech(translated, selected_language)
                        if audio_path:
                            audio_base64 = tts_engine.get_audio_base64(audio_path)
                            if audio_base64:
                                st.audio(f"data:audio/mp3;base64,{audio_base64}")
                            tts_engine.cleanup_audio(audio_path)
                        
                        last_spoken_text = translated
                        
                        # Add to history
                        timestamp = time.strftime("%H:%M:%S")
                        st.session_state.translation_history.append(
                            f"[{timestamp}] {stable_gesture} → {translated}"
                        )
                        
                        # Reset for next sign
                        classifier.reset_prediction()
            
            # Display frame
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            
            # Small delay
            time.sleep(0.01)
        
        cap.release()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>🏆 <b>Thales GenTech India Hackathon 2025</b></p>
        <p>Team InsigniaDevs | Theme: Inclusive EdTech</p>
        <p>Built with ❤️ using Streamlit, MediaPipe & TensorFlow</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
