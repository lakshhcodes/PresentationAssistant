import os
import time
import json
import pyaudio
import vosk
import pyautogui

# --- Configuration ---
# NOTE: Replace 'vosk-model-small-en-us-0.15' with the exact name of your downloaded model folder!
MODEL_NAME = "vosk-model-small-en-us-0.15" 

# Define the model path based on the current directory
MODEL_PATH = os.path.join(os.getcwd(), MODEL_NAME)

# Voice commands and their corresponding PyAutoGUI actions
COMMANDS = {
    "next slide": 'right',
    "next": 'right',
    "previous slide": 'left',
    "previous": 'left',
    "go back": 'left',
    "start presentation": 'f5',
    "end presentation": 'esc'
}

# --- Initialization ---
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
    print("Listening for commands (e.g., 'next slide', 'previous', 'end presentation')...")
    
except FileNotFoundError as e:
    print(f"ERROR: {e}")
    exit()
except Exception as e:
    print(f"An error occurred during Vosk/PyAudio initialization: {e}")
    exit()

# --- Voice Processing Loop ---

# Variables for command throttling (to prevent command repetition)
last_command_time = time.time()
COMMAND_COOLDOWN = 3.0 # Minimum seconds between successful voice commands

def process_command(text):
    """Checks the transcribed text against known commands and executes action."""
    global last_command_time
    
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

print("\nSpeak CLEARLY to issue a command.")
stream.start_stream()

try:
    while True:
        data = stream.read(4000, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            # Parse the final result from Vosk
            result = json.loads(rec.Result())
            
            # Process the full recognized text
            if result['text']:
                process_command(result['text'])

except KeyboardInterrupt:
    print("\nVoice Control Module shutting down...")
except Exception as e:
    print(f"An unexpected error occurred in the loop: {e}")

finally:
    # --- Cleanup ---
    if 'stream' in locals() and stream.is_active():
        stream.stop_stream()
        stream.close()
    if 'p' in locals():
        p.terminate()
    print("Voice Control cleanup complete.")