# Face Recognition Attendance System 🚀

A professional, production-ready web application and DevOps pipeline for automated student attendance tracking using facial recognition technology.

---

## 🏗️ DevOps Architecture & CI/CD Pipeline

```
Developer (git push)
      │
      ▼
GitHub Repository (main branch)
      │
      ▼ (Webhook / Polling)
Jenkins CI/CD Pipeline
      │──> 1. Checkout Source Code
      │──> 2. Install Python Dependencies
      │──> 3. Run Automated Unit Tests (pytest)
      │──> 4. Build Docker Image (face-attendance-app)
      │──> 5. Container Health Check Verification
      └──> 6. Deploy to AWS EC2
            │
            ▼
AWS EC2 Instance (Linux)
      └── Docker Container (Gunicorn + Flask)
            ├── Port 5000 Exposed
            └── Persistent Docker Volumes (Database & Student Photos)
```

---

## ✨ Features

- 🔍 **Automatic Face Recognition**: Identifies student faces in video streams or uploaded photos using OpenCV.
- ⏱️ **Duration-Based Marking**: Automatically tracks presence and marks attendance based on session thresholds.
- ✋ **Manual Override**: Teachers can manually mark attendance for single or multiple students.
- 📊 **Attendance Reports**: Generate daily attendance reports with statistics.
- 🎓 **Student Management**: Register students and upload face profiles.
- 🔒 **Student Portal**: Students log in with Roll Number to view subject-wise attendance.
- 🐳 **Dockerized Production Setup**: Served via Gunicorn WSGI server inside a Debian Linux container.
- 🧪 **Automated Testing Suite**: Built-in `pytest` unit tests for CI/CD integration.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, Flask 2.3.3
- **WSGI Server**: Gunicorn 21.2.0
- **Computer Vision**: OpenCV (`opencv-python`), NumPy, Pillow
- **Database**: SQLite 3
- **Testing**: Pytest
- **Containerization**: Docker & Docker Compose
- **CI/CD**: Jenkins Pipeline
- **Cloud Hosting**: AWS EC2 (Ubuntu / Amazon Linux)

---

## 🚀 Quick Start (Local Development)

### 1. Clone Repository
```bash
git clone https://github.com/basava2012/Face-Recognition.git
cd Face-Recognition
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows
source venv/bin/activate       # On Linux/macOS

pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 4. Run Automated Tests
```bash
python -m pytest
```

### 5. Start Application locally
```bash
python app/app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🐳 Running with Docker

### 1. Build Docker Image
```bash
docker build -t face-attendance-app .
```

### 2. Run Docker Container with Volumes
```bash
docker run -d -p 5000:5000 \
  --name attendance_container \
  -v attendance_db:/app/app/data \
  -v student_faces:/app/app/student_faces \
  face-attendance-app
```

### 3. Verify Container Health
```bash
curl http://localhost:5000/health
```
Expected response: `{"status": "healthy"}`

---

## 🧪 Automated Testing (CI/CD)

The project includes an automated test suite under `tests/`:
```bash
python -m pytest
```
Tests check:
- Endpoint health check (`/health` and `/api/health`).
- Login page rendering and authentication logic.
- API route authentication middleware.
- SQLite database creation and student registration logic.

---

## 🔐 Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `FLASK_SECRET` | Secret key for Flask session signing | `super-secret-change-me` |
| `ADMIN_USER` | Admin login username | `admin` |
| `ADMIN_PASS` | Admin login password | `admin@123` |
| `AUTO_MARK_MINUTES` | Minutes threshold to mark attendance | `45` |
| `PORT` | Application port | `5000` |

---

## 📄 License
Distributed under the MIT License.
