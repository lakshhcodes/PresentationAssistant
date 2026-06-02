# Classroom Presentation Assistant

A presentation assistant that enables hands-free slide navigation through hand gestures and voice commands. The application combines computer vision and speech recognition technologies to provide a seamless presentation experience without requiring a keyboard, mouse, or presentation remote.

## Overview

Classroom Presentation Assistant is designed to improve presentation delivery by allowing users to control slides naturally using gestures or voice commands. The system continuously processes webcam and microphone input to recognize predefined actions and execute slide navigation commands in real time.

## Features
### Gesture-Based Navigation
Using MediaPipe and OpenCV, the application tracks hand movements and interprets gestures for slide control.
| Gesture       | Action         |
| ------------- | -------------- |
| Swipe Inward  | Next Slide     |
| Swipe Outward | Previous Slide |
### Voice-Based Navigation
Using Vosk Speech Recognition, the application listens for specific commands and performs corresponding actions.
| Command          | Action                       |
| ---------------- | ---------------------------- |
| Next Slide       | Advance to the next slide    |
| Previous Slide   | Return to the previous slide |
| End Presentation | Exit the application         |

## Technology Stack
* Python 3.x
* OpenCV
* MediaPipe
* Vosk
* PyAudio
* PyAutoGUI

## Installation
### Clone the Repository
```bash
git clone https://github.com/lakshhcodes/PresentationAssistant.git
cd PresentationAssistant
```
### Install Dependencies
```bash
pip install -r requirements.txt
```
### Run the Application
```bash
python main.py
```
## System Workflow
Webcam Input
      ↓
Gesture Recognition
      ↓
Slide Navigation


Microphone Input
      ↓
Voice Recognition
      ↓
Slide Navigation

The application processes both visual and audio inputs simultaneously, allowing presenters to switch naturally between gesture and voice control.

## Applications
* Classroom Teaching
* Academic Presentations
* Project Demonstrations
* Workshops and Seminars
* Business Meetings

