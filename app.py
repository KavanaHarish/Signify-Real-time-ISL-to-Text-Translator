import streamlit as st
import cv2
import yaml
import time
import sys
import numpy as np

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
</style>
""", unsafe_allow_html=True)

# Load config
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
        st.title("⚙️ Settings")

        languages = {lang['code']: lang['name'] for lang in config['languages']}
        selected_language = st.selectbox(
            "Select Translation Language",
            options=list(languages.keys()),
            format_func=lambda x: languages[x]
        )

        enable_tts = st.checkbox("Enable Text-to-Speech", value=True)
        show_landmarks = st.checkbox("Show Hand Landmarks", value=True)
        show_confidence = st.checkbox("Show Confidence Score", value=True)

    # Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📹 Camera Input")
        start_button = st.button("Start Camera")

        video_placeholder = st.empty()

    with col2:
        st.subheader("💬 Output")

        detected_text = st.empty()
        translated_text = st.empty()
        confidence_display = st.empty()

    if start_button:
        st.session_state.camera_active = True

    if 'camera_active' not in st.session_state:
        st.session_state.camera_active = False

    # ✅ NEW CAMERA LOGIC (STREAMLIT FRIENDLY)
    if st.session_state.camera_active:
        st.info("Capture an image of the hand sign 👇")

        img_file = st.camera_input("Take a picture")

        if img_file is not None:
            file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
            frame = cv2.imdecode(file_bytes, 1)

            # Flip image
            frame = cv2.flip(frame, 1)

            # Detect hands
            frame, results = detector.find_hands(frame, draw=show_landmarks)

            # Get landmarks
            landmark_list = detector.get_position(frame, results)

            if landmark_list:
                fingers_up = detector.is_finger_up(landmark_list)

                gesture, confidence = classifier.classify_gesture_basic(
                    landmark_list, fingers_up
                )

                stable_gesture, stable_confidence = classifier.get_stable_prediction(
                    gesture, confidence,
                    threshold=config['gesture']['confidence_threshold']
                )

                if stable_gesture:
                    translated = classifier.translate_gesture(
                        stable_gesture, selected_language
                    )

                    detected_text.markdown(f"**Detected:** {stable_gesture.upper()}")
                    translated_text.markdown(f"**Translation:** {translated}")

                    if show_confidence:
                        confidence_display.markdown(
                            f"Confidence: {stable_confidence:.2%}"
                        )

                    # TTS
                    if enable_tts:
                        audio_path = tts_engine.text_to_speech(translated, selected_language)
                        if audio_path:
                            st.audio(audio_path)

            # Show image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown("Built for Hackathon 🚀")

if __name__ == "__main__":
    main()
