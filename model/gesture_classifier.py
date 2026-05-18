import numpy as np
import json
from collections import deque


class GestureClassifier:
    """
    Classify hand gestures into ISL signs using rule-based or ML approaches
    """
    def __init__(self, dictionary_path='data/isl_dictionary.json', sequence_length=30):
        self.sequence_length = sequence_length
        self.feature_sequence = deque(maxlen=sequence_length)
        self.current_prediction = None
        self.prediction_confidence = 0.0
        self.stable_prediction_count = 0
        self.stability_threshold = 15  # Number of consistent frames

        # Load ISL dictionary safely
        try:
            with open(dictionary_path, 'r', encoding='utf-8') as f:
                self.dictionary = json.load(f)
        except FileNotFoundError:
            print(f"[GestureClassifier] Dictionary not found at {dictionary_path}, using empty dict.")
            self.dictionary = {"signs": {}, "alphabet": {}}
        except json.JSONDecodeError as e:
            print(f"[GestureClassifier] JSON parse error: {e}, using empty dict.")
            self.dictionary = {"signs": {}, "alphabet": {}}

    def add_features(self, features):
        """
        Add current frame features to sequence buffer
        """
        if features is not None:
            self.feature_sequence.append(features)

    def classify_gesture_basic(self, landmark_list, fingers_up):
        """
        Basic rule-based gesture classification
        """
        if not landmark_list or fingers_up is None:
            return None, 0.0

        gesture = None
        confidence = 0.0

        # Count fingers up
        num_fingers = sum(fingers_up)

        # Simple gesture patterns
        if num_fingers == 0:
            gesture = "no"
            confidence = 0.85
        elif num_fingers == 5:
            gesture = "hello"
            confidence = 0.80
        elif num_fingers == 1 and fingers_up[1] == 1:  # Index finger only
            gesture = "question"
            confidence = 0.75
        elif num_fingers == 2 and fingers_up[1] == 1 and fingers_up[2] == 1:
            gesture = "yes"
            confidence = 0.80
        elif fingers_up == [1, 0, 0, 0, 1]:  # Thumb and pinky
            gesture = "help"
            confidence = 0.70

        return gesture, confidence

    def get_stable_prediction(self, current_gesture, confidence, threshold=0.75):
        """
        Return prediction only if it's stable across multiple frames
        """
        if confidence < threshold:
            return None, 0.0

        if current_gesture == self.current_prediction:
            self.stable_prediction_count += 1
        else:
            self.current_prediction = current_gesture
            self.stable_prediction_count = 1

        # Return prediction only if stable for enough frames
        if self.stable_prediction_count >= self.stability_threshold:
            return current_gesture, confidence

        return None, 0.0

    def translate_gesture(self, gesture, target_language='en'):
        """
        Translate gesture to target language using dictionary
        """
        if gesture is None:
            return None

        if gesture.lower() in self.dictionary.get('signs', {}):
            translation = self.dictionary['signs'][gesture.lower()].get(target_language, gesture)
            return translation

        # Check if it's an alphabet sign
        if gesture.upper() in self.dictionary.get('alphabet', {}):
            return gesture.upper()

        return gesture

    def reset_prediction(self):
        """
        Reset prediction state (useful when sign is complete)
        """
        self.current_prediction = None
        self.stable_prediction_count = 0
        self.feature_sequence.clear()

    def get_available_signs(self):
        """
        Get list of all available signs in dictionary
        """
        return list(self.dictionary.get('signs', {}).keys())

    def calculate_hand_angle(self, landmark_list):
        """
        Calculate hand orientation angle (useful for gesture recognition)
        """
        if len(landmark_list) < 21:
            return 0

        wrist = np.array([landmark_list[0][1], landmark_list[0][2]])
        middle_mcp = np.array([landmark_list[9][1], landmark_list[9][2]])

        vector = middle_mcp - wrist
        angle = np.arctan2(vector[1], vector[0]) * 180 / np.pi

        return angle

    def detect_static_vs_dynamic(self):
        """
        Detect if gesture is static (held) or dynamic (moving)
        Returns True if static, False if dynamic
        """
        if len(self.feature_sequence) < 10:
            return True

        recent_features = list(self.feature_sequence)[-10:]
        variance = np.var(recent_features, axis=0)
        avg_variance = np.mean(variance)

        return avg_variance < 0.001
