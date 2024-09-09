from flask import Flask, jsonify, request, render_template
import sqlite3
import face_recognition
import cv2
import numpy as np
from datetime import datetime, date
import hashlib
from firebase_sync import upload_attendance


app = Flask(__name__)

# Initialize database
def initialize_db():
    conn = sqlite3.connect("attendance.db")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ATTENDANCE (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            NAME TEXT NOT NULL,
            TIME TEXT NOT NULL,
            DATE TEXT NOT NULL,
            HASH TEXT UNIQUE
        )
    ''')
    conn.close()

initialize_db()

# Generate a hash for attendance record uniqueness
def generate_hash(name, current_date):
    return hashlib.sha256(f"{name}_{current_date}".encode()).hexdigest()

# Endpoint to start the attendance process

@app.route('/start_attendance', methods=['GET'])
def start_attendance():
    # Initialize camera
    video_capture = cv2.VideoCapture(0)

    # Load known faces (you may want to move this to a separate function for loading known faces)
    known_face_encodings, known_face_names = load_known_faces()

    while True:
        # Capture frame from the camera
        _, frame = video_capture.read()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Find all face locations and face encodings in the frame
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
                # Mark attendance
                mark_attendance(name)
                return jsonify({"message": f"Attendance marked for {name}."})

        # Display the frame (optional, for debugging)
        cv2.imshow('Video', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    video_capture.release()
    cv2.destroyAllWindows()

    return jsonify({"message": "Attendance process finished."})
def load_known_faces():
    known_face_encodings = []
    known_face_names = []

    # Correct paths to the image files
    files = [("Pooja", r"D:\ph\251065.jpg"), 
             ("Shek", r"D:\ph\251088.jpg"), 
             ("Vishnu", r"D:\ph\251116.jpg")]

    for name, file_path in files:
        image = face_recognition.load_image_file(file_path)
        encoding = face_recognition.face_encodings(image)[0]
        known_face_encodings.append(encoding)
        known_face_names.append(name)
    
    return known_face_encodings, known_face_names
def mark_attendance(name):
    conn = sqlite3.connect("attendance.db")
    cur = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_date = date.today().strftime("%Y-%m-%d")
    record_hash = generate_hash(name, current_date)

    # Check if the user has already been marked present today
    cur.execute("SELECT * FROM ATTENDANCE WHERE NAME = ? AND DATE = ?", (name, current_date))
    if cur.fetchone():
        print(f"Error: {name}'s attendance has already been marked for today.")
    else:
        try:
            cur.execute("INSERT INTO ATTENDANCE (NAME, TIME, DATE, HASH) VALUES (?, ?, ?, ?)", (name, current_time, current_date, record_hash))
            conn.commit()
            print(f"Attendance marked for {name} at {current_time}.")
        except sqlite3.IntegrityError:
            print(f"Duplicate entry detected for {name}. Skipping insertion.")
    conn.close()




# Endpoint to view attendance records
@app.route('/view_attendance', methods=['GET'])
def view_attendance():
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ATTENDANCE")
    rows = cursor.fetchall()
    conn.close()

    records = [{"id": row[0], "name": row[1], "time": row[2], "date": row[3]} for row in rows]
    return jsonify({"records": records})

# Home route to serve the HTML page
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/sync_firebase', methods=['GET'])
def sync_firebase():
    try:
        upload_attendance()
        return jsonify({"message": "Attendance data uploaded to Firebase successfully."})
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    app.run(debug=True)
