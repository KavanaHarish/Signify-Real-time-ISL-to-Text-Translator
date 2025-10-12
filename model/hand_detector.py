import cv2
import mediapipe as mp
import numpy as np

class HandDetector:
    """
    Hand detection and landmark extraction using MediaPipe
    """
    def __init__(self, mode=False, max_hands=2, detection_confidence=0.7, tracking_confidence=0.5):
        self.mode = mode
        self.max_hands = max_hands
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        
        # Initialize MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
    def find_hands(self, img, draw=True):
        """
        Detect hands in the image
        
        Args:
            img: Input image (BGR format)
            draw: Whether to draw landmarks on the image
            
        Returns:
            img: Image with drawn landmarks (if draw=True)
            results: MediaPipe hands results
        """
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)
        
        if results.multi_hand_landmarks and draw:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    img,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
        
        return img, results
    
    def get_position(self, img, results, hand_no=0):
        """
        Extract landmark positions from detected hand
        
        Args:
            img: Input image
            results: MediaPipe results
            hand_no: Which hand to extract (0 for first hand)
            
        Returns:
            landmark_list: List of [id, x, y] for each landmark
        """
        landmark_list = []
        
        if results.multi_hand_landmarks:
            if hand_no < len(results.multi_hand_landmarks):
                hand = results.multi_hand_landmarks[hand_no]
                
                for id, lm in enumerate(hand.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    landmark_list.append([id, cx, cy])
        
        return landmark_list
    
    def get_landmark_features(self, results):
        """
        Extract normalized landmark features for ML model
        
        Returns:
            features: Flattened array of x, y, z coordinates (63 features for 21 landmarks)
        """
        if not results.multi_hand_landmarks:
            return None
        
        hand = results.multi_hand_landmarks[0]
        features = []
        
        for landmark in hand.landmark:
            features.extend([landmark.x, landmark.y, landmark.z])
        
        return np.array(features)
    
    def get_hand_type(self, results, hand_no=0):
        """
        Determine if hand is left or right
        
        Returns:
            hand_type: "Left" or "Right"
        """
        if results.multi_handedness:
            if hand_no < len(results.multi_handedness):
                hand_type = results.multi_handedness[hand_no].classification[0].label
                return hand_type
        return None
    
    def calculate_distance(self, p1, p2):
        """
        Calculate Euclidean distance between two points
        """
        return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    
    def is_finger_up(self, landmark_list, finger_tip_ids=[4, 8, 12, 16, 20]):
        """
        Check which fingers are up (basic gesture recognition)
        
        Returns:
            fingers_up: List of boolean values for each finger
        """
        if len(landmark_list) < 21:
            return None
        
        fingers_up = []
        
        # Thumb (special case - check x coordinate)
        if landmark_list[4][1] < landmark_list[3][1]:  # Thumb tip < thumb IP joint
            fingers_up.append(1)
        else:
            fingers_up.append(0)
        
        # Other fingers
        for tip_id in finger_tip_ids[1:]:
            if landmark_list[tip_id][2] < landmark_list[tip_id - 2][2]:
                fingers_up.append(1)
            else:
                fingers_up.append(0)
        
        return fingers_up