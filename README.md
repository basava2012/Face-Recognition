# Face Recognition Attendance System

A modern web application for automated student attendance tracking using facial recognition technology.

## Features

✨ **Key Features:**
- 🔍 **Automatic Face Detection**: Automatically recognizes and tracks student faces
- ⏱️ **45-Minute Attendance Rule**: Students are automatically marked present after 45 minutes of detection
- ✋ **Manual Override**: Teachers can manually mark attendance anytime
- 📊 **Attendance Reports**: Generate detailed reports by date
- 👤 **Student Management**: Register students and manage their face profiles
- 💾 **SQLite Database**: Persistent storage of student records and attendance data
- 📱 **Responsive UI**: Works on desktop and tablet devices

## System Requirements

- Python 3.8+
- Webcam or camera device (for live detection)
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Installation

### 1. Clone/Extract the Project
```bash
cd "b:\Face detection"
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**On Windows (PowerShell):**
```bash
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**On Mac/Linux:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** The `dlib` and `face-recognition` libraries may require additional setup:
- On Windows, you might need to install Visual C++ Build Tools
- On Mac/Linux, ensure you have CMake installed

## Usage

### 1. Start the Application
```bash
python app/app.py
```

The application will start at `http://localhost:5000`

### 2. Register Students

**Home Tab:**
- View system information and features

**Students Tab:**
- **Register New Student**: Enter roll number, name, and email
- **Upload Face Image**: Upload a clear frontal face photo for each student

### 3. Start Attendance Session

**Attendance Tab:**
- Select the session date
- Click "Start Session"
- Upload an image containing student faces
- The system will automatically detect and mark attendance
- Use "Manual Attendance" to override attendance as needed

### 4. View Reports

**Report Tab:**
- Select a date
- Click "Generate Report"
- View attendance statistics and details

## Database Schema

### Students Table
```sql
- id (Primary Key)
- roll_number (Unique)
- name
- email
- created_at
```

### Attendance Table
```sql
- id (Primary Key)
- student_id (Foreign Key)
- session_date
- check_in_time
- check_out_time
- duration_minutes
- attendance_status (PRESENT, ABSENT, LATE)
- marked_by (System, Teacher)
```

### Face Encodings Table
```sql
- id (Primary Key)
- student_id (Foreign Key)
- encoding (Face encoding data)
- created_at
```

## File Structure

```
Face detection/
├── app/
│   ├── static/
│   │   ├── style.css           # CSS styling
│   │   └── script.js           # JavaScript functionality
│   ├── templates/
│   │   └── index.html          # Main HTML template
│   ├── student_faces/          # Stores student face images
│   ├── data/                   # Database and encodings
│   ├── app.py                  # Flask application
│   ├── database.py             # Database operations
│   └── face_recognition_module.py  # Face recognition logic
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## API Endpoints

### Students
- `GET /api/students` - Get all students
- `POST /api/students` - Add new student
- `POST /api/students/<id>/face` - Upload student face

### Attendance
- `POST /api/attendance/start-session` - Start attendance session
- `POST /api/attendance/recognize` - Process frame for face recognition
- `POST /api/attendance/manual-mark` - Manually mark attendance
- `GET /api/attendance/report?date=YYYY-MM-DD` - Get attendance report
- `GET /api/attendance/<student_id>/<date>` - Get individual record

## How Attendance Works

### Automatic Detection
1. Teacher uploads an image during an active session
2. System detects all faces in the image
3. Each detected student is automatically checked in
4. System tracks how long each student is detected across multiple frames
5. After 45 minutes of accumulated detection, student is marked PRESENT

### Manual Marking
1. Teacher can manually select a student
2. Choose attendance status (Present, Absent, Late)
3. Click "Mark Attendance"
4. Record is immediately saved to database

## Configuration

You can modify attendance rules by editing `app.py`:
- Change the 45-minute threshold in `mark_attendance_auto()` function
- Adjust face recognition tolerance in `recognize_faces()` function

## Troubleshooting

### Issue: "No module named 'face_recognition'"
**Solution:** Ensure you've installed all requirements and activated the virtual environment
```bash
pip install -r requirements.txt
```

### Issue: Face recognition not working
**Solution:** 
- Ensure face images are clear and well-lit
- Upload images showing frontal face view
- Check that student has at least one registered face

### Issue: Database locked error
**Solution:** Restart the Flask application and ensure no other instances are running

### Issue: Camera not accessible
**Solution:** The web version uses image upload simulation. For live webcam integration, additional browser APIs are needed.

## Performance Tips

- Upload clear, well-lit face images
- Use consistent lighting for best results
- Ensure only one student's face per registration image
- Keep attendance sessions to reasonable duration
- Archive old attendance records regularly

## Future Enhancements

- Real-time webcam streaming integration
- Multi-face recognition in single frame
- Automatic rollcall reports generation
- Export attendance to Excel/PDF
- Mobile app support
- Integration with school management system
- Liveness detection (prevent photos)
- Attendance statistics dashboard

## License

This project is provided as-is for educational purposes.

## Support

For issues or questions, check the console logs and ensure:
1. Flask server is running
2. Database file exists in `app/data/`
3. Student faces are registered properly
4. All dependencies are installed
