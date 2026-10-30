# 🏙️ CivicAI – Smart Civic Complaint Management System

**CivicAI** is a web-based civic complaint management platform developed using Python Flask and SQLite. It helps citizens report public issues such as road damage, garbage accumulation, drainage problems, water supply issues, and street lighting failures.

The system helps organize citizen complaints, automatically categorize issues, recommend responsible departments, identify possible duplicate reports, and track complaint status through an interactive dashboard.

## 🚀 Features

- **Complaint Registration:** Citizens can submit complaints with descriptions, locations, and optional photos.
- **Automatic Categorization:** Identifies complaint categories using rule-based keyword matching.
- **Priority Detection:** Automatically identifies high-priority complaints based on urgent keywords.
- **Department Recommendation:** Suggests the appropriate department for each complaint.
- **Duplicate Detection:** Identifies potentially similar complaints reported at the same location.
- **Complaint Tracking:** Citizens can track complaint progress using a unique tracking link.
- **Admin Dashboard:** Displays complaint statistics, categories, and status information.
- **Interactive Map:** Shows complaint locations, hotspots, and area-wise patterns.
- **Status Management:** Departments can update complaints as Pending, Assigned, In Progress, or Resolved.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web framework |
| SQLite | Database |
| HTML | Web page structure |
| CSS | User interface styling |
| JavaScript | Interactive features |
| Leaflet.js | Interactive maps |
| OpenStreetMap | Map data |

## 📂 Project Structure

```text
CivicAI-Project/
│
├── app.py
├── requirements.txt
├── README.md
│
├── uploads/
│   └── .gitkeep
│
└── civicai.db (created automatically)
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

### 2. Open the project folder

```bash
cd CivicAI-Project
```

### 3. Create a virtual environment

```bash
python -m venv .venv
```

### 4. Activate the virtual environment

**Windows:**
```powershell
.venv\Scripts\Activate.ps1
```

**Mac/Linux:**
```bash
source .venv/bin/activate
```

### 5. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 6. Run the application

```bash
python app.py
```

### 7. Open in your browser

**Complaint Form:**
http://127.0.0.1:5001/

**Admin Dashboard:**
http://127.0.0.1:5001/complaints

## 📊 Complaint Categories

- Road Damage
- Garbage
- Drainage
- Water Supply
- Street Lighting
- Other

## 🎯 Project Objective

The main objective of CivicAI is to improve communication between citizens and local authorities by providing a simple digital platform for reporting and managing civic issues.

It aims to make complaint handling more organized, transparent, and efficient.

## 🔮 Future Enhancements

- AI-powered image recognition for civic issues.
- Citizen and administrator login authentication.
- Real-time complaint notifications.
- Advanced analytics and reporting.
- Mobile application integration.

## ⚠️ Project Limitations

CivicAI is currently a prototype using rule-based classification rather than a trained AI model. Demo complaint data and map coordinates are fictional. It is intended for educational and demonstration purposes.

## 👨‍💻 Developer

Developed as a project to demonstrate web development, database management, and smart civic issue management using Python and Flask.

**Project Name:** CivicAI  
**Domain:** Smart City / Civic Technology  
**Backend:** Python Flask  
**Database:** SQLite
