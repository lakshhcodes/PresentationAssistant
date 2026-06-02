import cv2
import mediapipe as mp
import pyautogui
import time 

# --- Configuration Constants ---
WEBCAM_INDEX = 0             # Index of the camera to use
GESTURE_DELAY = 2.0          # Seconds: Minimum time between slide changes (throttling)
SWIPE_THRESHOLD = 0.07       # Normalized units (0.0 to 1.0): Minimum horizontal movement for a swipe
HISTORY_SIZE = 8             # Number of frames to check for a swipe (smoother detection)
WINDOW_NAME = 'Classroom Presentation Assistant: Gesture Mode'
EXIT_KEY = 27                # ASCII for 'ESC' key

# --- Initialization ---
# Initialize MediaPipe Hands solution
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    min_detection_confidence=0.7, 
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# Open the default webcam
cap = cv2.VideoCapture(WEBCAM_INDEX)

print("Starting Gesture Control Module. Press 'ESC' to exit.")

# Variables for the slide control logic (Index Finger Tip)
index_x_history = []          # Stores recent x-coordinates for reliable swipe detection
last_slide_time = time.time() # Stores the timestamp of the last slide change

while cap.isOpened():
    success, image = cap.read()
    if not success:
        continue
        
    # 1. Image Preprocessing
    # Flip the image horizontally for a natural 'mirror' view (Crucial for correct handedness!)
    image = cv2.flip(image, 1) 
    # Convert the BGR image (OpenCV default) to RGB (MediaPipe requirement)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # 2. Process with MediaPipe
    image_rgb.flags.writeable = False # Read-only for performance
    results = hands.process(image_rgb)
    image_rgb.flags.writeable = True # Now writable again for drawing

    # 3. Gesture Detection and Drawing
    if results.multi_hand_landmarks:
        # Loop through ALL detected hands (max 2)
        for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
            
            # 3A. IDENTIFY HANDEDNESS
            is_right_hand = (results.multi_handedness[i].classification[0].label == 'Right')
            
            # --- Draw landmarks for visualization ---
            color = (0, 255, 0) if is_right_hand else (0, 0, 255) # Green for Right, Blue for other
            mp_drawing.draw_landmarks(
                image, 
                hand_landmarks, 
                mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=color, thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
            )
            
            # 3B. ONLY PROCESS THE RIGHT HAND (the one you are using)
            if is_right_hand:
                
                # Get the normalized x-coordinate of the Index Finger Tip (Landmark 8)
                tip_landmark = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                current_x = tip_landmark.x
                
                # Get pixel coordinates for visual feedback
                h, w, c = image.shape
                tip_x_px = int(tip_landmark.x * w)
                tip_y_px = int(tip_landmark.y * h)
                
                # Draw a large yellow circle on the tracked index finger for feedback
                cv2.circle(image, (tip_x_px, tip_y_px), 15, (0, 255, 255), cv2.FILLED) 

                # 4. Update History
                index_x_history.append(current_x)
                if len(index_x_history) > HISTORY_SIZE:
                    index_x_history.pop(0) # Maintain the fixed buffer size
                    
                # 5. Implement Smoother Swipe Logic 
                # Check for cool-down AND ensure history buffer is full
                if (time.time() - last_slide_time) > GESTURE_DELAY and len(index_x_history) == HISTORY_SIZE:
                    
                    start_x = index_x_history[0]  # Oldest position in the buffer
                    delta_x = current_x - start_x # Total movement over the history period
                    
                    if delta_x > SWIPE_THRESHOLD:
                        # Index Finger moved significantly Right (out) → Left (in) 
                        # Inward swipe is NEXT slide (e.g., swiping a touchscreen from right to left)
                        print(">> NEXT SLIDE (Swipe Inward)")
                        pyautogui.press('right')
                        last_slide_time = time.time()
                        index_x_history = [] # Clear history after a successful swipe

                    elif delta_x < -SWIPE_THRESHOLD:
                        # Index Finger moved significantly Left (in) → Right (out)
                        # Outward swipe is PREVIOUS slide 
                        print("<< PREVIOUS SLIDE (Swipe Outward)")
                        pyautogui.press('left')
                        last_slide_time = time.time()
                        index_x_history = [] # Clear history after a successful swipe
                        
            # If it's not the right hand, we skip the swipe logic for this hand, but draw the landmarks.
            
    # If no hands are detected, clear the history to prevent false triggers when a hand reappears
    if not results.multi_hand_landmarks:
        index_x_history = [] 

    # 6. Display the output
    cv2.imshow(WINDOW_NAME, image)
    
    # Exit loop when 'ESC' (key 27) is pressed
    if cv2.waitKey(5) & 0xFF == EXIT_KEY:
        break
        
# --- Cleanup ---
cap.release()
cv2.destroyAllWindows()
print("Gesture Control Module shutdown complete.")