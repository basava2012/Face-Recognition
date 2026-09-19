import cv2
import numpy as np
import os
import hashlib
from pathlib import Path

STUDENT_FACES_DIR = os.path.join(os.path.dirname(__file__), 'student_faces')

# Load the pre-trained Haar Cascade classifier for face detection
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def ensure_student_dir():
    """Ensure student faces directory exists"""
    if not os.path.exists(STUDENT_FACES_DIR):
        os.makedirs(STUDENT_FACES_DIR)

def detect_faces(image):
    """Detect faces in an image using Haar Cascade"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return faces

def compute_face_encoding(image, face_location):
    """
    Compute a simple encoding for a face using histogram
    This is a lightweight alternative to deep learning models
    """
    x, y, w, h = face_location
    face_roi = image[y:y+h, x:x+w]
    
    # Convert to HSV and compute histogram
    hsv = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256])
    
    # Normalize and flatten
    encoding = cv2.normalize(hist, hist).flatten()
    return encoding

def save_student_face(student_id, image_path, output_name=None):
    """Save and encode a student's face"""
    ensure_student_dir()
    
    student_dir = os.path.join(STUDENT_FACES_DIR, str(student_id))
    if not os.path.exists(student_dir):
        os.makedirs(student_dir)
    
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        return False, "Could not read image"
    
    # Detect faces
    faces = detect_faces(image)
    
    if len(faces) == 0:
        return False, "No face detected in image"
    elif len(faces) > 1:
        return False, "Multiple faces detected. Please upload image with only one person"
    
    # Save the face image
    if output_name is None:
        output_name = f"face_{len(os.listdir(student_dir)) + 1}.jpg"
    
    output_path = os.path.join(student_dir, output_name)
    cv2.imwrite(output_path, image)
    
    return True, output_path

def get_student_encoding(student_id):
    """Get stored encoding for a student"""
    student_dir = os.path.join(STUDENT_FACES_DIR, str(student_id))
    
    if not os.path.exists(student_dir):
        return None
    
    # Get first available face encoding
    for filename in sorted(os.listdir(student_dir)):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(student_dir, filename)
            image = cv2.imread(image_path)
            if image is not None:
                faces = detect_faces(image)
                if len(faces) > 0:
                    encoding = compute_face_encoding(image, faces[0])
                    return encoding
    
    return None

def compare_faces(face1_encoding, face2_encoding, threshold=0.5):
    """
    Compare two face encodings
    Returns confidence score between 0 and 1
    """
    if face1_encoding is None or face2_encoding is None:
        return 0
    
    # Ensure same length
    min_len = min(len(face1_encoding), len(face2_encoding))
    face1 = face1_encoding[:min_len]
    face2 = face2_encoding[:min_len]
    
    # Compute Chi-Square distance
    # OpenCV builds expose CHISQR/CHISQR_ALT; some examples wrongly use CHISQRT
    # Pick the first available compatible constant.
    method = getattr(cv2, 'HISTCMP_CHISQRT', None)
    if method is None:
        method = getattr(cv2, 'HISTCMP_CHISQR', None)
    if method is None:
        method = getattr(cv2, 'HISTCMP_CHISQR_ALT', None)
    if method is None:
        # Fallback to correlation inverse (less ideal but keeps flow)
        method = getattr(cv2, 'HISTCMP_CORREL', 0)
    distance = cv2.compareHist(face1.reshape(-1, 1), face2.reshape(-1, 1), method)
    
    # Convert distance to confidence (inverted and normalized)
    confidence = max(0, 1 - (distance / 10))
    return confidence

def recognize_faces(frame, known_encodings, student_ids, tolerance=0.3):
    """
    Recognize faces in a frame
    
    Args:
        frame: OpenCV image frame
        known_encodings: List of known face encodings
        student_ids: List of student IDs corresponding to encodings
        tolerance: Confidence threshold for face matching
    
    Returns:
        List of tuples (student_id, confidence, location)
    """
    # Detect faces in the frame
    faces = detect_faces(frame)
    results = []
    
    for face_location in faces:
        # Compute encoding for detected face
        face_encoding = compute_face_encoding(frame, face_location)
        
        # Compare with known encodings
        best_match_id = None
        best_confidence = 0
        
        for known_encoding, student_id in zip(known_encodings, student_ids):
            confidence = compare_faces(face_encoding, known_encoding)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match_id = student_id
        
        # Accept match if confidence is above threshold
        if best_confidence >= tolerance and best_match_id is not None:
            results.append((best_match_id, best_confidence, face_location))
    
    return results

def load_all_encodings(students):
    """Load all student face encodings"""
    known_encodings = []
    student_ids = []
    
    for student_id, _, _, _ in students:
        encoding = get_student_encoding(student_id)
        if encoding is not None:
            known_encodings.append(encoding)
            student_ids.append(student_id)
    
    return known_encodings, student_ids

def capture_face_from_webcam(student_id, num_images=3):
    """Capture face images from webcam"""
    ensure_student_dir()
    
    student_dir = os.path.join(STUDENT_FACES_DIR, str(student_id))
    if not os.path.exists(student_dir):
        os.makedirs(student_dir)
    
    cap = cv2.VideoCapture(0)
    captured_count = 0
    frame_count = 0
    
    while captured_count < num_images:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Capture every 10 frames to get different angles
        if frame_count % 10 == 0:
            faces = detect_faces(frame)
            
            if len(faces) == 1:  # Only one face in frame
                # Save the frame
                image_path = os.path.join(student_dir, f'face_{captured_count + 1}.jpg')
                cv2.imwrite(image_path, frame)
                captured_count += 1
                print(f"Captured face {captured_count}/{num_images}")
            elif len(faces) == 0:
                print("No face detected, please look at the camera")
            else:
                print("Multiple faces detected, please ensure only one person is visible")
        
        # Display the frame with instructions
        cv2.putText(frame, f"Captured: {captured_count}/{num_images}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow('Capture Face', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    return captured_count == num_images
