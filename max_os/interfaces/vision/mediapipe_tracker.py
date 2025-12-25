"""Unified hand, face, and pose tracking using MediaPipe Holistic."""

from __future__ import annotations

from typing import Any

try:
    import cv2
    import mediapipe as mp
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore
    mp = None  # type: ignore
    np = None  # type: ignore


class MediaPipeTracker:
    """Unified hand, face, and pose tracking using MediaPipe Holistic."""

    def __init__(
        self,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        enable_segmentation: bool = False,
        refine_face_landmarks: bool = True,
    ):
        """Initialize MediaPipe Holistic tracker.

        Args:
            model_complexity: Complexity of the model (0, 1, or 2)
            min_detection_confidence: Minimum confidence for detection
            min_tracking_confidence: Minimum confidence for tracking
            enable_segmentation: Enable segmentation mask
            refine_face_landmarks: Enable refined face landmarks
        """
        if mp is None or cv2 is None or np is None:
            raise RuntimeError(
                "mediapipe, opencv-python, and numpy not installed. "
                "Install with: pip install 'maxos[google]'"
            )

        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic(
            static_image_mode=False,
            model_complexity=model_complexity,
            smooth_landmarks=True,
            enable_segmentation=enable_segmentation,
            refine_face_landmarks=refine_face_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def process_frame(self, frame: Any) -> dict[str, Any]:
        """Process camera frame and extract all landmarks.

        Args:
            frame: Camera frame (numpy array in BGR format)

        Returns:
            Dictionary containing landmarks and detected gestures
        """
        # Convert BGR to RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # Process with MediaPipe
        results = self.holistic.process(image)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        return {
            "face_landmarks": results.face_landmarks,
            "pose_landmarks": results.pose_landmarks,
            "left_hand_landmarks": results.left_hand_landmarks,
            "right_hand_landmarks": results.right_hand_landmarks,
            "gestures": self._detect_gestures(results),
            "eye_gaze": self._calculate_eye_gaze(results.face_landmarks),
        }

    def _detect_gestures(self, results: Any) -> list[str]:
        """Detect predefined gestures (point, fist, open palm, etc.).

        Args:
            results: MediaPipe Holistic results

        Returns:
            List of detected gesture names
        """
        gestures = []

        # Check left hand
        if results.left_hand_landmarks:
            left_gesture = self._classify_hand_gesture(results.left_hand_landmarks)
            if left_gesture:
                gestures.append(f"left_{left_gesture}")

        # Check right hand
        if results.right_hand_landmarks:
            right_gesture = self._classify_hand_gesture(results.right_hand_landmarks)
            if right_gesture:
                gestures.append(f"right_{right_gesture}")

        return gestures

    def _classify_hand_gesture(self, hand_landmarks: Any) -> str | None:
        """Classify hand gesture based on landmarks.

        Args:
            hand_landmarks: MediaPipe hand landmarks

        Returns:
            Gesture name or None
        """
        if not hand_landmarks:
            return None

        # Get landmark positions
        landmarks = hand_landmarks.landmark

        # Simple gesture detection based on finger positions
        # This is a basic implementation - can be enhanced with ML models

        # Count extended fingers
        fingers_extended = []

        # Thumb (different logic due to orientation)
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        fingers_extended.append(thumb_tip.x < thumb_ip.x)  # Simplified

        # Other fingers (index to pinky)
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]

        for tip_idx, pip_idx in zip(finger_tips, finger_pips, strict=True):
            tip = landmarks[tip_idx]
            pip = landmarks[pip_idx]
            fingers_extended.append(tip.y < pip.y)  # Finger pointing up

        extended_count = sum(fingers_extended)

        # Classify gestures
        if extended_count == 0:
            return "fist"
        elif extended_count == 5:
            return "open_palm"
        elif extended_count == 1 and fingers_extended[1]:  # Index finger
            return "pointing"
        elif extended_count == 2 and fingers_extended[1] and fingers_extended[2]:
            return "peace_sign"
        elif extended_count == 1 and fingers_extended[0]:  # Thumb
            return "thumbs_up"

        return None

    def _calculate_eye_gaze(self, face_landmarks: Any) -> dict[str, Any] | None:
        """Calculate eye gaze direction for cursor control.

        Args:
            face_landmarks: MediaPipe face landmarks

        Returns:
            Dictionary with gaze coordinates or None
        """
        if not face_landmarks:
            return None

        # Extract eye landmarks (MediaPipe Face Mesh indices)
        # These are approximate iris centers in the 478-point face mesh
        try:
            landmarks = face_landmarks.landmark
            left_eye = landmarks[468]  # Left iris center
            right_eye = landmarks[473]  # Right iris center

            # Calculate average gaze position
            gaze_x = (left_eye.x + right_eye.x) / 2
            gaze_y = (left_eye.y + right_eye.y) / 2

            return {
                "x": gaze_x,
                "y": gaze_y,
                "normalized": True,  # 0-1 range
            }
        except (IndexError, AttributeError):
            return None

    def draw_landmarks(
        self,
        image: Any,
        results: dict[str, Any],
        draw_face: bool = True,
        draw_pose: bool = True,
        draw_hands: bool = True,
    ) -> Any:
        """Draw landmarks on image.

        Args:
            image: Image to draw on
            results: Results from process_frame
            draw_face: Whether to draw face landmarks
            draw_pose: Whether to draw pose landmarks
            draw_hands: Whether to draw hand landmarks

        Returns:
            Image with landmarks drawn
        """
        # Draw face landmarks
        if draw_face and results.get("face_landmarks"):
            self.mp_drawing.draw_landmarks(
                image,
                results["face_landmarks"],
                self.mp_holistic.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style(),
            )

        # Draw pose landmarks
        if draw_pose and results.get("pose_landmarks"):
            self.mp_drawing.draw_landmarks(
                image,
                results["pose_landmarks"],
                self.mp_holistic.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
            )

        # Draw hand landmarks
        if draw_hands:
            if results.get("left_hand_landmarks"):
                self.mp_drawing.draw_landmarks(
                    image,
                    results["left_hand_landmarks"],
                    self.mp_holistic.HAND_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_hand_landmarks_style(),
                )
            if results.get("right_hand_landmarks"):
                self.mp_drawing.draw_landmarks(
                    image,
                    results["right_hand_landmarks"],
                    self.mp_holistic.HAND_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_hand_landmarks_style(),
                )

        return image

    def close(self):
        """Clean up resources."""
        if hasattr(self, "holistic"):
            self.holistic.close()
