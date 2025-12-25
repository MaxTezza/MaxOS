"""Test MediaPipe hand/face/pose tracking."""

import cv2
import numpy as np

from max_os.interfaces.vision.mediapipe_tracker import MediaPipeTracker


def test_mediapipe():
    """Test MediaPipe tracking with camera."""
    print("👁️ Testing MediaPipe Holistic Tracking")
    print("=" * 60)

    try:
        tracker = MediaPipeTracker()
        print("✅ MediaPipe tracker initialized successfully")
        print()
        print("Opening camera...")

        # Open camera
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("❌ Could not open camera")
            print("   Make sure you have a camera connected")
            return

        print("✅ Camera opened successfully")
        print()
        print("Controls:")
        print("  - Press 'q' to quit")
        print("  - Make hand gestures to test detection")
        print("  - Watch for gesture labels on screen")
        print()

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read frame")
                break

            # Process frame
            results = tracker.process_frame(frame)

            # Draw landmarks
            frame = tracker.draw_landmarks(frame, results)

            # Add info overlay
            frame_count += 1
            info_text = f"Frame: {frame_count}"
            cv2.putText(
                frame,
                info_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            # Display gestures
            if results["gestures"]:
                gesture_text = f"Gestures: {', '.join(results['gestures'])}"
                cv2.putText(
                    frame,
                    gesture_text,
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    2,
                )
                print(f"Detected: {results['gestures']}")

            # Display eye gaze
            if results["eye_gaze"]:
                gaze = results["eye_gaze"]
                gaze_text = f"Gaze: ({gaze['x']:.2f}, {gaze['y']:.2f})"
                cv2.putText(
                    frame,
                    gaze_text,
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            cv2.imshow("MediaPipe Test", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        tracker.close()
        cv2.destroyAllWindows()

        print()
        print(f"✅ Test completed. Processed {frame_count} frames.")

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Make sure you have installed:")
        print("  pip install 'maxos[google]'")


if __name__ == "__main__":
    test_mediapipe()
