import multiprocessing
import os
import sys

# --- GESTURE CONTROL LIBRARIES ---
import cv2
import mediapipe as mp
import pyautogui
import time 

# --- VOICE CONTROL LIBRARIES ---
import json
import pyaudio
import vosk
# pyautogui is already imported

# ===================================================================
# --- GESTURE CONTROL MODULE (Function to be run in a separate process) ---
# ===================================================================

def gesture_control_module():
    """Handles all webcam-based gesture detection and slide control."""

    # --- Configuration Constants ---
    WEBCAM_INDEX = 0             # Index of the camera to use
    GESTURE_DELAY = 2.0          # Seconds: Minimum time between slide changes (throttling)
    SWIPE_THRESHOLD = 0.07       # Normalized units (0.0 to 1.0): Minimum horizontal movement for a swipe
    HISTORY_SIZE = 8             # Number of frames to check for a swipe (smoother detection)
    WINDOW_NAME = 'Classroom Presentation Assistant: Gesture Mode'
    EXIT_KEY = 27                # ASCII for 'ESC' key

    # --- Initialization ---
    try:
        # Initialize MediaPipe Hands solution
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            min_detection_confidence=0.7, 
            min_tracking_confidence=0.5
        )
        mp_drawing = mp.solutions.drawing_utils

        # Open the default webcam
        cap = cv2.VideoCapture(WEBCAM_INDEX)
        if not cap.isOpened():
            print(f"ERROR: Could not open webcam at index {WEBCAM_INDEX}.")
            return

        print("--- Gesture Control Module Initialized ---")
        print("Starting Gesture Control Module. Press 'ESC' to exit the window.")

        # Variables for the slide control logic (Index Finger Tip)
        index_x_history = []     # Stores recent x-coordinates for reliable swipe detection
        last_slide_time = time.time() # Stores the timestamp of the last slide change

        while cap.isOpened():
            success, image = cap.read()
            if not success:
                # print("Ignoring empty camera frame.")
                time.sleep(0.01) # Avoid busy loop
                continue
                
            # 1. Image Preprocessing
            image = cv2.flip(image, 1) # Flip horizontally for natural 'mirror' view
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 2. Process with MediaPipe
            image_rgb.flags.writeable = False
            results = hands.process(image_rgb)
            image_rgb.flags.writeable = True

            # 3. Gesture Detection and Drawing
            if results.multi_hand_landmarks:
                for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    
                    # 3A. IDENTIFY HANDEDNESS
                    # Check if multi_handedness list is valid and has classification data
                    if results.multi_handedness and len(results.multi_handedness[i].classification) > 0:
                         is_right_hand = (results.multi_handedness[i].classification[0].label == 'Right')
                    else:
                         is_right_hand = False # Default to false if classification is missing
                    
                    # --- Draw landmarks for visualization ---
                    color = (0, 255, 0) if is_right_hand else (0, 0, 255) 
                    mp_drawing.draw_landmarks(
                        image, 
                        hand_landmarks, 
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=color, thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )
                    
                    # 3B. ONLY PROCESS THE RIGHT HAND
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
                            index_x_history.pop(0)
                            
                        # 5. Implement Smoother Swipe Logic 
                        if (time.time() - last_slide_time) > GESTURE_DELAY and len(index_x_history) == HISTORY_SIZE:
                            start_x = index_x_history[0]
                            delta_x = current_x - start_x
                            
                            if delta_x > SWIPE_THRESHOLD:
                                # Swipe Inward (Right to Left in the mirror view) -> NEXT SLIDE
                                print("[GESTURE] >> NEXT SLIDE (Swipe Inward)")
                                pyautogui.press('right')
                                last_slide_time = time.time()
                                index_x_history = [] 

                            elif delta_x < -SWIPE_THRESHOLD:
                                # Swipe Outward (Left to Right in the mirror view) -> PREVIOUS SLIDE
                                print("[GESTURE] << PREVIOUS SLIDE (Swipe Outward)")
                                pyautogui.press('left')
                                last_slide_time = time.time()
                                index_x_history = []
                            
            # If no hands are detected, clear the history 
            if not results.multi_hand_landmarks:
                index_x_history = [] 

            # 6. Display the output
            cv2.imshow(WINDOW_NAME, image)
            
            # Exit loop when 'ESC' (key 27) is pressed
            if cv2.waitKey(5) & 0xFF == EXIT_KEY:
                break
                
    except Exception as e:
        print(f"An error occurred in the Gesture Control Module: {e}")

    finally:
        # --- Cleanup ---
        if 'cap' in locals() and cap.isOpened():
             cap.release()
        cv2.destroyAllWindows()
        print("Gesture Control Module shutdown complete.")
        # Terminate the parent process as well if the gesture window is closed
        # os._exit(0) # Use this if closing one must close all. Removed to allow other process to continue.

# ===================================================================
# --- VOICE CONTROL MODULE (Function to be run in a separate process) ---
# ===================================================================

def voice_control_module():
    """Handles all microphone-based speech recognition and slide control."""

    # NOTE: Replace 'vosk-model-small-en-us-0.15' with the exact name of your downloaded model folder!
    MODEL_NAME = "vosk-model-small-en-us-0.15" 
    MODEL_PATH = os.path.join(os.getcwd(), MODEL_NAME)
    COMMAND_COOLDOWN = 3.0 # Minimum seconds between successful voice commands

    COMMANDS = {
        "next slide": 'right',
        "next": 'right',
        "previous slide": 'left',
        "previous": 'left',
        "go back": 'left',
        "start presentation": 'f5',
        "end presentation": 'esc'
    }

    # Variables for command throttling
    last_command_time = time.time()

    def process_command(text):
        """Checks the transcribed text against known commands and executes action."""
        nonlocal last_command_time
        
        current_time = time.time()
        
        # Check cooldown first
        if (current_time - last_command_time) < COMMAND_COOLDOWN:
            # print(f"Command ignored due to cooldown ({COMMAND_COOLDOWN}s).")
            return

        for command_phrase, action_key in COMMANDS.items():
            if command_phrase in text:
                print(f"🎤 COMMAND DETECTED: '{command_phrase.upper()}' -> Action: {action_key.upper()}")
                
                # Execute the action
                pyautogui.press(action_key)
                
                # Reset cooldown timer
                last_command_time = current_time
                return # Exit after the first command is processed

    try:
        # 1. Load the Vosk model
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Vosk model not found at: {MODEL_PATH}. Please download and place the folder here.")
            
        model = vosk.Model(MODEL_PATH)
        rec = vosk.KaldiRecognizer(model, 16000)
        
        # 2. Setup PyAudio
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        frames_per_buffer=8000)

        print("--- Voice Control Module Initialized ---")
        print(f"Model loaded from: {MODEL_NAME}")
        print(f"Listening for commands. Cooldown: {COMMAND_COOLDOWN}s.")
        print("Speak CLEARLY to issue a command (e.g., 'next slide', 'previous', 'end presentation').")
        stream.start_stream()

        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                # Parse the final result from Vosk
                result = json.loads(rec.Result())
                
                # Process the full recognized text
                if result['text']:
                    process_command(result['text'])
            # NOTE: If we used PartialResult, we could display the partial recognition.
            # partial = json.loads(rec.PartialResult())
            # print(f"Partial: {partial['partial']}", end='\r')

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        # sys.exit(1) # Don't exit the whole program here, just this process.
    except KeyboardInterrupt:
        print("\nVoice Control Module received exit signal.")
    except Exception as e:
        print(f"An unexpected error occurred in the Voice Control Module: {e}")

    finally:
        # --- Cleanup ---
        if 'stream' in locals() and stream.is_active():
            stream.stop_stream()
            stream.close()
        if 'p' in locals():
            p.terminate()
        print("Voice Control cleanup complete.")


# ===================================================================
# --- MAIN EXECUTION ---
# ===================================================================

if __name__ == '__main__':
    print("Starting Classroom Presentation Assistant...")
    print("------------------------------------------")

    # 1. Create process for Gesture Control
    gesture_process = multiprocessing.Process(target=gesture_control_module)
    
    # 2. Create process for Voice Control
    voice_process = multiprocessing.Process(target=voice_control_module)
    
    # 3. Start both processes
    try:
        gesture_process.start()
        voice_process.start()
        
        # 4. Wait for both processes to complete (or for user to interrupt)
        # We join them so the main script waits for them.
        gesture_process.join()
        voice_process.join()

    except KeyboardInterrupt:
        print("\nMain process received KeyboardInterrupt. Terminating children...")
        # Cleanly terminate the processes if the user hits Ctrl+C on the main console
        if gesture_process.is_alive():
            gesture_process.terminate()
        if voice_process.is_alive():
            voice_process.terminate()
            
    finally:
        print("------------------------------------------")
        print("Classroom Presentation Assistant shutdown complete.")