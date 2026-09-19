// Tab Navigation
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;
        
        // Remove active class from all buttons and sections
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
        
        // Add active class to clicked button and corresponding section
        btn.classList.add('active');
        document.getElementById(tabName).classList.add('active');
    });
});

// Set today's date as default
document.getElementById('sessionDate').valueAsDate = new Date();
document.getElementById('reportDate').valueAsDate = new Date();

// Load students on page load
window.addEventListener('load', () => {
    loadStudents();
});

// Load Students (updated to allow clicking a student to view details)
async function loadStudents() {
    try {
        const response = await fetch('/api/students');
        const students = await response.json();
        
        // Update student list
        const studentsList = document.getElementById('studentsList');
        if (students.length === 0) {
            studentsList.innerHTML = '<p>No students registered yet</p>';
        } else {
            studentsList.innerHTML = students.map(student => `
                <div class="student-card" data-id="${student.id}" onclick="showStudentDetails(${student.id})">
                    <p class="roll-number">${student.roll_number}</p>
                    <p class="name">${student.name}</p>
                    <p style="font-size: 0.9em; color: #999;">${student.email || 'No email'}</p>
                </div>
            `).join('');
        }
        
        // Update student selects
        updateStudentSelects(students);
    } catch (error) {
        console.error('Error loading students:', error);
    }
}

function updateStudentSelects(students) {
    const studentSelect = document.getElementById('studentSelect');
    if (studentSelect) {
        studentSelect.innerHTML = '<option value="">-- Choose a student --</option>' +
            students.map(s => `<option value="${s.id}">${s.roll_number} - ${s.name}</option>`).join('');
    }

    const manualSelect = document.getElementById('manualStudentSelect');
    if (manualSelect) {
        manualSelect.innerHTML = students.map(s => `<option value="${s.id}">${s.roll_number} - ${s.name}</option>`).join('');
    }
}

// Add Student Form
document.getElementById('addStudentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const rollNumber = document.getElementById('rollNumber').value;
    const studentName = document.getElementById('studentName').value;
    const studentEmail = document.getElementById('studentEmail').value;
    const messageDiv = document.getElementById('addStudentMessage');
    
    try {
        const response = await fetch('/api/students', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                roll_number: rollNumber,
                name: studentName,
                email: studentEmail
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage(messageDiv, 'Student added successfully!', 'success');
            document.getElementById('addStudentForm').reset();
            loadStudents();
        } else {
            showMessage(messageDiv, data.message || 'Failed to add student', 'error');
        }
    } catch (error) {
        showMessage(messageDiv, 'Error: ' + error.message, 'error');
    }
});

// --- Registration camera (for capturing face from live camera) ---
let registrationStream = null;
async function startRegistrationCamera(){
    const sel = document.getElementById('studentSelect');
    if(!sel.value){
        showMessage(document.getElementById('uploadMessage'), 'Select a student first to register face', 'error');
        return;
    }
    const video = document.getElementById('registrationVideo');
    try{
        registrationStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        video.srcObject = registrationStream;
        document.getElementById('registrationCamera').style.display = 'block';
        document.getElementById('captureFaceBtn').style.display = 'inline-block';
    }catch(err){
        showMessage(document.getElementById('uploadMessage'), 'Cannot access camera: '+err.message, 'error');
    }
}

function stopRegistrationCamera(){
    if(registrationStream){
        registrationStream.getTracks().forEach(t=>t.stop());
        registrationStream = null;
    }
    document.getElementById('registrationCamera').style.display = 'none';
    document.getElementById('captureFaceBtn').style.display = 'none';
}

async function captureStudentFace(){
    const sel = document.getElementById('studentSelect');
    const studentId = sel.value;
    const messageDiv = document.getElementById('uploadMessage');
    if(!studentId){ showMessage(messageDiv, 'Select student first', 'error'); return; }
    const video = document.getElementById('registrationVideo');
    const canvas = document.getElementById('registrationCanvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob)=>{
        const formData = new FormData();
        formData.append('file', blob, 'capture.jpg');
        try{
            const res = await fetch(`/api/students/${studentId}/face`, { method: 'POST', body: formData });
            const data = await res.json();
            if(res.ok){
                showMessage(messageDiv, 'Face captured & registered', 'success');
                stopRegistrationCamera();
                loadStudents();
            } else {
                showMessage(messageDiv, data.message || 'Failed to register face', 'error');
            }
        }catch(err){
            showMessage(messageDiv, 'Error: '+err.message, 'error');
        }
    }, 'image/jpeg', 0.95);
}

// --- Attendance camera and timer ---
let attendanceStream = null;
let attendanceVideoElem = document.getElementById('attendanceVideo');
let attendanceTimerInterval = null;
let attendanceEndTime = null;
let recognitionInterval = null; // defined for completeness
let sessionActive = false;

async function startCamera(){
    // attempt to start real camera for attendance
    try{
        if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
            startCameraSimulation();
            return;
        }
        attendanceStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        attendanceVideoElem = document.getElementById('attendanceVideo');
        attendanceVideoElem.srcObject = attendanceStream;
        attendanceVideoElem.style.display = 'block';
        document.getElementById('cameraStatus').textContent = '📹 Camera started for session';
    }catch(err){
        console.warn('Camera start failed, falling back to upload mode', err);
        startCameraSimulation();
    }
}

function startCameraSimulation(){
    const cameraPlaceholder = document.querySelector('.camera-placeholder');
    // remove existing upload prompt if present
    const existing = document.getElementById('simUploadBox');
    if(existing) existing.remove();

    const uploadPrompt = document.createElement('div');
    uploadPrompt.id = 'simUploadBox';
    uploadPrompt.innerHTML = `
        <p>📸 Upload an image to simulate face detection:</p>
        <input type="file" id="testImageUpload" accept="image/*" style="padding: 10px;">
        <button onclick="processTestImage()" class="btn btn-primary" style="margin-top: 10px;">Process Image</button>
    `;
    cameraPlaceholder.appendChild(uploadPrompt);
}

async function startSession() {
    const sessionDate = document.getElementById('sessionDate').value;
    const sessionStatus = document.getElementById('sessionStatus');
    const durationMin = parseInt(document.getElementById('sessionDuration').value || '45', 10);
    const subject = (document.getElementById('sessionSubject') && document.getElementById('sessionSubject').value) || '';
    
    if (!sessionDate) {
        showMessage(sessionStatus, 'Please select a date', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/attendance/start-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_date: sessionDate, duration_minutes: durationMin, subject: subject })
        });
        const data = await response.json();
        if (response.ok) {
            sessionActive = true;
            sessionStatus.style.display = 'block';
            showMessage(sessionStatus, `Session started for ${sessionDate}`, 'info');
            document.getElementById('cameraStatus').textContent = '📹 Session Active - Detecting Faces...';
            // start camera
            await startCamera();
            // start timer
            attendanceEndTime = Date.now() + durationMin * 60 * 1000;
            document.getElementById('sessionTimer').style.display = 'block';
            updateTimerDisplay();
            attendanceTimerInterval = setInterval(updateTimerDisplay, 1000);
            // begin periodic recognition so server can track presence duration
            if(recognitionInterval){ clearInterval(recognitionInterval); }
            recognitionInterval = setInterval(recognizeLoopTick, 2000); // every 2s
        }
    } catch (error) {
        showMessage(sessionStatus, 'Error: ' + error.message, 'error');
    }
}

function updateTimerDisplay(){
    if(!attendanceEndTime) return;
    const remaining = Math.max(0, attendanceEndTime - Date.now());
    const hrs = String(Math.floor(remaining/3600000)).padStart(2,'0');
    const mins = String(Math.floor((remaining%3600000)/60000)).padStart(2,'0');
    const secs = String(Math.floor((remaining%60000)/1000)).padStart(2,'0');
    document.getElementById('timerDisplay').textContent = `${hrs}:${mins}:${secs}`;
    if(remaining<=0){
        // time's up - capture attendance
        clearInterval(attendanceTimerInterval);
        attendanceTimerInterval = null;
        document.getElementById('sessionTimer').style.display = 'none';
        processAttendanceCapture();
    }
}

async function processAttendanceCapture(){
    const sessionDate = document.getElementById('sessionDate').value;
    const sessionStatus = document.getElementById('sessionStatus');
    try{
        let blob = null;
        if(attendanceStream && attendanceVideoElem && attendanceVideoElem.videoWidth){
            const canvas = document.getElementById('videoCanvas');
            canvas.style.display = 'block';
            canvas.width = attendanceVideoElem.videoWidth;
            canvas.height = attendanceVideoElem.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(attendanceVideoElem, 0, 0, canvas.width, canvas.height);
            blob = await new Promise(res=>canvas.toBlob(res, 'image/jpeg', 0.9));
        } else {
            // ask user to upload an image
            const fileInput = document.getElementById('testImageUpload');
            if(fileInput && fileInput.files && fileInput.files[0]){
                blob = fileInput.files[0];
            }
        }
        if(!blob){
            showMessage(sessionStatus, 'No frame available to process attendance', 'error');
            return;
        }
        const formData = new FormData();
        formData.append('frame', blob, 'frame.jpg');
        formData.append('session_date', sessionDate);
        const res = await fetch('/api/attendance/recognize', { method: 'POST', body: formData });
        const data = await res.json();
        if(data.success){
            updateRecognizedList(data.recognized);
            // if admin, mark present via complete-session endpoint
            try{
                const who = await (await fetch('/api/whoami')).json();
                if(who.role === 'admin'){
                    const ids = data.recognized.map(r=>r.id);
                    if(ids.length){
                        const subject = document.getElementById('sessionSubject') ? document.getElementById('sessionSubject').value : '';
                        await fetch('/api/attendance/complete-session', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ session_date: sessionDate, student_ids: ids, subject: subject }) });
                    }
                }
            }catch(err){ console.warn('whoami/complete-session failed', err); }
            // show report for date
            await generateReport();
        } else {
            showMessage(sessionStatus, data.message || 'Recognition failed', 'error');
        }
    }catch(err){
        showMessage(sessionStatus, 'Error processing attendance: '+err.message, 'error');
    }finally{
        stopSession();
    }
}

async function recognizeLoopTick(){
    if(!sessionActive) return;
    try{
        const sessionDate = document.getElementById('sessionDate').value;
        let blob = null;
        if(attendanceStream && attendanceVideoElem && attendanceVideoElem.videoWidth){
            const canvas = document.getElementById('videoCanvas');
            canvas.width = attendanceVideoElem.videoWidth;
            canvas.height = attendanceVideoElem.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(attendanceVideoElem, 0, 0, canvas.width, canvas.height);
            blob = await new Promise(res=>canvas.toBlob(res, 'image/jpeg', 0.8));
        }
        if(!blob) return;
        const formData = new FormData();
        formData.append('frame', blob, 'frame.jpg');
        formData.append('session_date', sessionDate);
        const res = await fetch('/api/attendance/recognize', { method: 'POST', body: formData });
        const data = await res.json();
        if(data && data.success){
            updateRecognizedList(data.recognized);
        }
    }catch(e){
        // ignore transient errors during loop
    }
}

function stopSession() {
    sessionActive = false;
    if (recognitionInterval) {
        clearInterval(recognitionInterval);
        recognitionInterval = null;
    }
    if(attendanceTimerInterval){
        clearInterval(attendanceTimerInterval);
        attendanceTimerInterval = null;
    }
    attendanceEndTime = null;
    const sessionStatus = document.getElementById('sessionStatus');
    document.getElementById('cameraStatus').textContent = 'Session ended';
    // stop camera streams
    if(registrationStream){ registrationStream.getTracks().forEach(t=>t.stop()); registrationStream=null; }
    if(attendanceStream){ attendanceStream.getTracks().forEach(t=>t.stop()); attendanceStream=null; }
    // hide video/canvas and clear source to fully release camera
    if(attendanceVideoElem){
        attendanceVideoElem.pause();
        attendanceVideoElem.srcObject = null;
        attendanceVideoElem.style.display = 'none';
    }
    const canvas = document.getElementById('videoCanvas');
    if(canvas){ canvas.style.display = 'none'; const ctx = canvas.getContext('2d'); ctx && ctx.clearRect(0,0,canvas.width,canvas.height); }
    // clear recognized list UI
    const rec = document.getElementById('recognizedList');
    if(rec){ rec.innerHTML = ''; }
    const sim = document.getElementById('simUploadBox'); if(sim) sim.remove();
    const uploadPrompt = document.querySelector('input#testImageUpload');
    if (uploadPrompt) {
        uploadPrompt.parentElement.remove();
    }
    // Ask server to finalize and return present/absent lists
    (async ()=>{
        try{
            const sessionDate = document.getElementById('sessionDate').value;
            const resp = await fetch('/api/attendance/stop-session', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ session_date: sessionDate }) });
            const data = await resp.json();
            if(data && data.success){
                showPresentAbsent(data.present, data.absent);
                showMessage(sessionStatus, 'Session stopped', 'info');
            } else {
                showMessage(sessionStatus, (data && data.message) || 'Session stopped', 'info');
            }
        }catch(e){
            showMessage(sessionStatus, 'Session stopped', 'info');
        }
    })();
}

// Show details for a student when clicked
async function showStudentDetails(studentId){
    try{
        const res = await fetch(`/api/students/${studentId}`);
        const data = await res.json();
        if(!data.success) return;
        const s = data.student;
        // determine if current user is admin
        let isAdmin = false;
        try{
            const who = await (await fetch('/api/whoami')).json();
            isAdmin = who.role === 'admin';
        }catch(e){ /* ignore */ }

        let html = `<p><strong>Roll:</strong> ${s.roll_number}</p>`;
        html += `<p><strong>Name:</strong> ${s.name}</p>`;
        html += `<p><strong>Email:</strong> ${s.email || '-'}</p>`;
        // faces
        const facesResp = await fetch(`/api/students/${studentId}/faces`);
        const faces = await facesResp.json();
        if(faces.images && faces.images.length){
            html += `<div style="margin-top:8px; display:flex; flex-wrap:wrap; gap:8px;">` + faces.images.map(i=>{
                const filename = i.split('/').pop();
                const imgHtml = `<div style="text-align:center;"><img src="${i}" style="max-width:120px; display:block; border:1px solid #ddd;"/>` +
                    (isAdmin ? `<button class="btn" style="margin-top:6px;" onclick="deleteFace(${studentId}, '${filename.replace(/'/g, "\\'")}')">Delete</button>` : '') +
                    `</div>`;
                return imgHtml;
            }).join('') + `</div>`;
        } else {
            html += `<p>No faces registered</p>`;
        }

        // container for edit UI / messages
        html += `<div id="studentEditContainer_${studentId}" style="margin-top:10px;"></div>`;
        html += `<div id="studentEditMessage_${studentId}" class="message" style="display:none;margin-top:8px;"></div>`;

        document.getElementById('studentDetailContent').innerHTML = html;
        document.getElementById('studentDetails').style.display = 'block';

        // If current user is admin, show Edit button and inline form placeholder
        if(isAdmin){
            const container = document.getElementById(`studentEditContainer_${studentId}`);
            container.innerHTML = `
                <button class="btn" onclick="openEditStudentForm(${studentId})">Edit Details</button>
                <div id="editForm_${studentId}" style="display:none; margin-top:8px; border-top:1px solid #eee; padding-top:8px;">
                    <h4>Edit Student</h4>
                    <div class="form-group"><label>Roll Number:</label><input type="text" id="editRoll_${studentId}" class="input"/></div>
                    <div class="form-group"><label>Name:</label><input type="text" id="editName_${studentId}" class="input"/></div>
                    <div class="form-group"><label>Email:</label><input type="email" id="editEmail_${studentId}" class="input"/></div>
                    <button class="btn btn-primary" onclick="submitEditStudent(${studentId})">Save</button>
                    <button class="btn" onclick="cancelEditStudent(${studentId})">Cancel</button>
                </div>
            `;
        }

    }catch(err){ console.error(err); }
}

// Delete a face image (admin-only)
async function deleteFace(studentId, filename){
    if(!confirm('Delete this face image?')) return;
    try{
        const res = await fetch(`/api/students/${studentId}/faces`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();
        const msgDiv = document.getElementById(`studentEditMessage_${studentId}`);
        if(res.ok && data.success){
            showMessage(msgDiv, 'Image deleted', 'success');
            // refresh details
            setTimeout(()=> showStudentDetails(studentId), 500);
        } else {
            showMessage(msgDiv, data.message || 'Delete failed', 'error');
        }
    }catch(e){
        const msgDiv = document.getElementById(`studentEditMessage_${studentId}`);
        showMessage(msgDiv, 'Error: '+e.message, 'error');
    }
}

// Open edit form and populate with current values
function openEditStudentForm(studentId){
    const res = document.getElementById(`studentEditContainer_${studentId}`);
    if(!res) return;
    const detailHtml = document.getElementById('studentDetailContent').innerHTML;
    // Extract current values from displayed details (simple approach)
    // Alternatively we could re-fetch student, but reuse existing data
    (async ()=>{
        try{
            const r = await fetch(`/api/students/${studentId}`);
            const d = await r.json();
            if(!d.success) return;
            document.getElementById(`editRoll_${studentId}`).value = d.student.roll_number || '';
            document.getElementById(`editName_${studentId}`).value = d.student.name || '';
            document.getElementById(`editEmail_${studentId}`).value = d.student.email || '';
            document.getElementById(`editForm_${studentId}`).style.display = 'block';
        }catch(e){ console.error(e); }
    })();
}

function cancelEditStudent(studentId){
    const form = document.getElementById(`editForm_${studentId}`);
    if(form) form.style.display = 'none';
}

// Submit edited details to server
async function submitEditStudent(studentId){
    const roll = document.getElementById(`editRoll_${studentId}`).value.trim();
    const name = document.getElementById(`editName_${studentId}`).value.trim();
    const email = document.getElementById(`editEmail_${studentId}`).value.trim();
    const msgDiv = document.getElementById(`studentEditMessage_${studentId}`);

    try{
        const res = await fetch(`/api/students/${studentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ roll_number: roll, name: name, email: email })
        });
        const data = await res.json();
        if(res.ok){
            showMessage(msgDiv, data.message || 'Updated', 'success');
            // hide form and refresh lists/details
            cancelEditStudent(studentId);
            loadStudents();
            // refresh displayed details
            setTimeout(()=> showStudentDetails(studentId), 500);
        } else {
            showMessage(msgDiv, data.message || 'Update failed', 'error');
        }
    }catch(e){
        showMessage(msgDiv, 'Error: '+e.message, 'error');
    }
}

// Generate Report
async function generateReport() {
    const reportDate = document.getElementById('reportDate').value;
    
    if (!reportDate) {
        alert('Please select a date');
        return;
    }
    
    try {
        const response = await fetch(`/api/attendance/report?date=${reportDate}`);
        const data = await response.json();
        
        if (data.success) {
            displayReport(data.report, reportDate);
        } else {
            alert('Error generating report: ' + data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function displayReport(report, date) {
    const reportContainer = document.getElementById('reportContainer');
    const reportTitle = document.getElementById('reportTitle');
    const reportBody = document.getElementById('reportBody');
    
    reportTitle.textContent = `Attendance Report - ${date}`;
    
    reportBody.innerHTML = report.map(row => `
        <tr>
            <td>${row.roll_number}</td>
            <td>${row.name}</td>
            <td>
                <span class="status-${row.status.toLowerCase()}">
                    ${row.status}
                </span>
            </td>
            <td>${row.check_in_time || '-'}</td>
            <td>${row.duration_minutes || '-'}</td>
        </tr>
    `).join('');
    
    // Calculate statistics
    const presentCount = report.filter(r => r.status === 'PRESENT').length;
    const absentCount = report.filter(r => r.status === 'ABSENT').length;
    
    document.getElementById('totalStudents').textContent = report.length;
    document.getElementById('presentCount').textContent = presentCount;
    document.getElementById('absentCount').textContent = absentCount;
    
    reportContainer.style.display = 'block';
}

// Helper function to show messages
function showMessage(element, message, type) {
    element.textContent = message;
    element.className = 'message ' + type;
    element.style.display = 'block';
    
    if (type === 'success') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 3000);
    }
}

function showPresentAbsent(present, absent){
    const container = document.getElementById('recognizedList');
    if(!container) return;
    const presentHtml = (present||[]).map(p=>`<li>${p.roll_number} - ${p.name}</li>`).join('') || '<li>None</li>';
    const absentHtml = (absent||[]).map(a=>`<li>${a.roll_number} - ${a.name}</li>`).join('') || '<li>None</li>';
    container.innerHTML = `
        <div class="present-absent">
            <div>
                <h4>Present</h4>
                <ul>${presentHtml}</ul>
            </div>
            <div>
                <h4>Absent</h4>
                <ul>${absentHtml}</ul>
            </div>
        </div>`;
}

// Update recognized students list box
function updateRecognizedList(recognized){
    const list = document.getElementById('recognizedList');
    if(!list) return;
    if(!recognized || !recognized.length){
        list.innerHTML = '<p>No students detected yet</p>';
        return;
    }
    list.innerHTML = recognized.map(r => `
        <div class="student-card small">
            <p class="roll-number">${r.roll_number || ''}</p>
            <p class="name">${r.name || ''} <span style="color:#999; font-size:0.9em;">(${r.confidence || 0}%)</span></p>
        </div>
    `).join('');
}

// Mark Manual Attendance
async function markManualAttendance() {
    const select = document.getElementById('manualStudentSelect');
    const messageDiv = document.getElementById('manualMessage');
    const status = document.getElementById('attendanceStatus').value || 'PRESENT';
    const sessionDate = document.getElementById('sessionDate').value || document.getElementById('reportDate').value || new Date().toISOString().split('T')[0];
    const subject = (document.getElementById('sessionSubject') && document.getElementById('sessionSubject').value) || '';

    if (!select) return;

    // Support single or multiple selected options
    const selectedOptions = Array.from(select.selectedOptions)
        .map(opt => opt.value)
        .filter(val => val !== "");

    if (selectedOptions.length === 0) {
        showMessage(messageDiv, 'Please select at least one student', 'error');
        return;
    }

    try {
        const response = await fetch('/api/attendance/manual-mark', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_ids: selectedOptions,
                session_date: sessionDate,
                status: status,
                subject: subject
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showMessage(messageDiv, data.message || 'Attendance marked successfully!', 'success');
            
            // Sync report date and generate/refresh report so changes reflect immediately
            const reportDateElem = document.getElementById('reportDate');
            if (reportDateElem) {
                reportDateElem.value = sessionDate;
            }
            await generateReport();
        } else {
            showMessage(messageDiv, data.message || 'Failed to mark attendance', 'error');
        }
    } catch (error) {
        showMessage(messageDiv, 'Error: ' + error.message, 'error');
    }
}
