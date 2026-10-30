"""Beginner-friendly CivicAI demo built with Flask and SQLite."""

from datetime import datetime
import difflib
import html
import json
import os
import re
import sqlite3
import uuid

from flask import Flask, abort, redirect, render_template_string, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
DATABASE = "civicai.db"
UPLOAD_FOLDER = "uploads"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
STATUSES = ["Pending", "Assigned", "In Progress", "Resolved"]
DEPARTMENTS = ["Public Works", "Sanitation", "Water Department", "Street Lighting", "Emergency Services", "General Services"]


def connect_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def categorize_complaint(description):
    text = description.lower()
    categories = {
        "Drainage": ["drain", "sewage", "waterlogging", "flood", "stormwater", "manhole"],
        "Garbage": ["garbage", "waste", "trash", "rubbish", "litter", "dumping", "bin"],
        "Road Damage": ["road", "pothole", "street", "pavement", "sidewalk", "crack", "asphalt"],
        "Water Supply": ["water supply", "water leak", "drinking water", "pipe burst", "no water", "tap"],
        "Street Lighting": ["streetlight", "street light", "lamp", "lighting", "dark", "light pole"],
    }
    for category, words in categories.items():
        if any(word in text for word in words):
            return category
    return "Other"


def recommend_department(category):
    return {
        "Drainage": "Public Works", "Garbage": "Sanitation", "Road Damage": "Public Works",
        "Water Supply": "Water Department", "Street Lighting": "Street Lighting",
        "Other": "General Services",
    }.get(category, "General Services")


def make_summary(description):
    """Use the first sentence and keep dashboard summaries short."""
    sentence = re.split(r"(?<=[.!?])\s+", description.strip())[0]
    if len(sentence) > 120:
        sentence = sentence[:117].rsplit(" ", 1)[0] + "..."
    return sentence


def calculate_priority(description):
    text = description.lower()
    urgent_words = ["dangerous", "emergency", "accident", "flood", "school entrance", "hospital", "injury", "exposed wire", "fire", "burst pipe"]
    return "High" if any(word in text for word in urgent_words) else "Normal"


def priority_reason(description, priority):
    """Explain which text signals led to the prototype priority decision."""
    text = description.lower()
    triggers = [word for word in ["dangerous", "emergency", "accident", "flood", "school entrance",
                                   "hospital", "injury", "exposed wire", "fire", "burst pipe"] if word in text]
    if priority == "High":
        return "High priority because the report mentions: " + ", ".join(triggers) + "."
    return "Normal priority because none of the prototype's urgent hazard keywords were found. Please review manually."


def find_duplicate(conn, description, location):
    """Flag a likely duplicate in the same named area using a simple text score."""
    normalized = " ".join(re.findall(r"[a-z0-9]+", description.lower()))
    for row in conn.execute("SELECT id, description, location FROM complaints ORDER BY id DESC"):
        same_place = row["location"].strip().lower() == location.strip().lower()
        other = " ".join(re.findall(r"[a-z0-9]+", row["description"].lower()))
        if same_place and difflib.SequenceMatcher(None, normalized, other).ratio() >= 0.72:
            return row["id"]
    return None


def sample_complaints():
    """Thirty-six fictional reports, clustered around four demo neighborhoods."""
    places = [
        ("Maple Junction", 40.7128, -74.0060), ("Maple Junction", 40.7134, -74.0052),
        ("Riverside Market", 40.7182, -74.0120), ("Riverside Market", 40.7175, -74.0111),
        ("Cedar School", 40.7068, -74.0012), ("Cedar School", 40.7074, -74.0005),
        ("Hillview Clinic", 40.7210, -74.0015), ("Hillview Clinic", 40.7204, -74.0022),
    ]
    issues = [
        ("A deep pothole is damaging cars and is dangerous near the school entrance.", "High"),
        ("Overflowing garbage bins and litter have been left beside the bus stop.", "Normal"),
        ("A blocked storm drain is causing waterlogging after rain.", "Normal"),
        ("Street light is out and the sidewalk is very dark at night.", "Normal"),
        ("A water pipe burst is flooding the road near the hospital.", "High"),
        ("Broken pavement creates a trip hazard for pedestrians.", "Normal"),
        ("Sewage is overflowing from the drain and creating an emergency health concern.", "High"),
        ("Illegal waste dumping is blocking the street and attracting pests.", "Normal"),
        ("No drinking water is reaching homes after a water supply interruption.", "Normal"),
    ]
    people = ["Asha Patel", "Jordan Lee", "Sam Rivera", "Morgan Chen", "Riley Shah", "Taylor Kim"]
    result = []
    for index in range(36):
        place, lat, lon = places[index % len(places)]
        description, priority = issues[index % len(issues)]
        # Repeat reports in selected places to provide visible clusters and duplicate flags.
        if index in (9, 18, 27):
            description = issues[0][0]
            place = "Maple Junction"
            lat, lon = 40.7128, -74.0060
        result.append({"name": people[index % len(people)], "description": description,
                       "location": place, "lat": lat, "lon": lon,
                       "created_at": f"2026-10-{(index % 28) + 1:02d} 09:00"})
    return result


def init_db():
    """Create or migrate schema without dropping or replacing existing complaints."""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL,
            location TEXT NOT NULL, category TEXT NOT NULL, priority TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL)""")
        existing = {row[1] for row in conn.execute("PRAGMA table_info(complaints)")}
        additions = {"department": "TEXT NOT NULL DEFAULT 'General Services'", "summary": "TEXT NOT NULL DEFAULT ''",
                     "latitude": "REAL", "longitude": "REAL", "duplicate_of": "INTEGER",
                     "category_hint": "TEXT NOT NULL DEFAULT 'Not specified'", "image_path": "TEXT"}
        for column, definition in additions.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE complaints ADD COLUMN {column} {definition}")
        conn.execute("UPDATE complaints SET status='Pending' WHERE status='Submitted'")
        for row in conn.execute("SELECT id, description, category, department, summary FROM complaints").fetchall():
            category = categorize_complaint(row["description"])
            conn.execute("UPDATE complaints SET category=?, department=?, summary=? WHERE id=?",
                         (category, recommend_department(category), make_summary(row["description"]), row["id"]))
        # Insert demo records only once; this adds examples without touching existing user records.
        conn.execute("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        seeded = conn.execute("SELECT value FROM app_metadata WHERE key='sample_data_v1'").fetchone()
        if not seeded:
            for item in sample_complaints():
                category = categorize_complaint(item["description"])
                duplicate = find_duplicate(conn, item["description"], item["location"])
                conn.execute("""INSERT INTO complaints
                    (name, description, location, category, priority, status, created_at, department, summary, latitude, longitude, duplicate_of)
                    VALUES (?, ?, ?, ?, ?, 'Pending', ?, ?, ?, ?, ?, ?)""",
                    (item["name"], item["description"], item["location"], category,
                     calculate_priority(item["description"]), item["created_at"], recommend_department(category),
                     make_summary(item["description"]), item["lat"], item["lon"], duplicate))
            conn.execute("INSERT INTO app_metadata VALUES ('sample_data_v1', 'added')")


FORM = """<!doctype html><html><head><title>CivicAI — Report an issue</title><meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'><style>body{font:16px Arial;background:#f1f5f9;margin:0;padding:16px;color:#172554}.box{max-width:700px;margin:20px auto;background:white;padding:26px;border-radius:14px;box-shadow:0 4px 18px #0001}h1{color:#155e75}label{display:block;margin-top:16px;font-weight:bold}input,textarea,select{box-sizing:border-box;width:100%;padding:12px;margin-top:8px;border:1px solid #cbd5e1;border-radius:7px;font-size:16px}button{margin-top:18px;padding:13px 20px;background:#0e7490;color:white;border:0;border-radius:7px;font-size:16px;cursor:pointer}a{color:#0e7490}#pickmap{height:250px;margin-top:8px;border-radius:8px}.help{color:#64748b;font-size:13px}</style></head>
<body><main class='box'><h1>🏙️ CivicAI</h1><h2>Report a Community Problem</h2><p>Usually takes under a minute. Add a description, choose a category, and share where it happened.</p>
{% if message %}<p style='color:#b91c1c'>{{ message }}</p>{% endif %}<form method='post' enctype='multipart/form-data'>
<label for='name'>Your Name</label><input id='name' name='name' required maxlength='100' placeholder='Enter your name'>
<label for='location'>Problem Location</label><input id='location' name='location' required maxlength='200' placeholder='Street, area or landmark'>
<label>Optional map pin</label><div id='pickmap' role='application' aria-label='Tap the map to add a location pin'></div><p class='help'>Tap the map to attach coordinates. The map is centered on the fictional demo area; you can still enter any address above.</p>
<input type='hidden' id='latitude' name='latitude'><input type='hidden' id='longitude' name='longitude'>
<label for='category_hint'>Choose a category</label><select id='category_hint' name='category_hint'><option>Not specified</option><option>Drainage</option><option>Garbage</option><option>Road Damage</option><option>Water Supply</option><option>Street Lighting</option><option>Other</option></select>
<label for='description'>Describe the Problem</label><textarea id='description' name='description' rows='4' required maxlength='2000' placeholder='What happened? Mention urgency or impact if relevant.'></textarea>
<label for='image'>Optional photo</label><input id='image' name='image' type='file' accept='image/png,image/jpeg,image/gif,image/webp'><p class='help'>Images up to 5 MB; do not include sensitive personal information.</p>
<button type='submit'>Submit Complaint</button></form><p><a href='/complaints'>View the complaints dashboard</a></p></main>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script><script>const picker=L.map('pickmap').setView([40.713,-74.006],13);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap'}).addTo(picker);let pin;picker.on('click',e=>{document.getElementById('latitude').value=e.latlng.lat.toFixed(6);document.getElementById('longitude').value=e.latlng.lng.toFixed(6);if(pin)pin.remove();pin=L.marker(e.latlng).addTo(picker);});</script></body></html>"""


@app.route("/", methods=["GET", "POST"])
def home():
    message = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        category_hint = request.form.get("category_hint", "Not specified")
        if category_hint not in ["Not specified", "Drainage", "Garbage", "Road Damage", "Water Supply", "Street Lighting", "Other"]:
            category_hint = "Not specified"
        if not name or not description or not location:
            message = "Please complete all fields."
        else:
            uploaded = request.files.get("image")
            image_path = None
            if uploaded and uploaded.filename:
                filename = secure_filename(uploaded.filename)
                extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                if extension not in ALLOWED_IMAGE_EXTENSIONS:
                    return render_template_string(FORM, message="Please upload a PNG, JPG, GIF, or WebP image.")
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                saved_name = f"{uuid.uuid4().hex}.{extension}"
                uploaded.save(os.path.join(UPLOAD_FOLDER, saved_name))
                image_path = saved_name
            latitude = request.form.get("latitude", "").strip()
            longitude = request.form.get("longitude", "").strip()
            try:
                latitude, longitude = (float(latitude), float(longitude)) if latitude and longitude else (None, None)
                if latitude is not None and not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    raise ValueError
            except ValueError:
                return render_template_string(FORM, message="The map pin coordinates were invalid. Please choose the pin again.")
            with connect_db() as conn:
                inferred = categorize_complaint(description)
                category = inferred if inferred != "Other" else (category_hint if category_hint != "Not specified" else inferred)
                duplicate = find_duplicate(conn, description, location)
                cursor = conn.execute("""INSERT INTO complaints (name,description,location,category,priority,status,created_at,department,summary,duplicate_of,latitude,longitude,category_hint,image_path)
                    VALUES (?,?,?,?,?,'Pending',?,?,?,?,?,?,?,?)""",
                    (name, description, location, category, calculate_priority(description), datetime.now().strftime("%Y-%m-%d %H:%M"),
                     recommend_department(category), make_summary(description), duplicate, latitude, longitude, category_hint, image_path))
                complaint_id = cursor.lastrowid
            return redirect(url_for("track_complaint", complaint_id=complaint_id))
    return render_template_string(FORM, message=message)


@app.route("/track/<int:complaint_id>")
def track_complaint(complaint_id):
    with connect_db() as conn:
        row = conn.execute("SELECT id,category,summary,status,department,priority,duplicate_of FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    if row is None:
        abort(404)
    return render_template_string(TRACK, row=row, statuses=STATUSES)


@app.route("/uploads/<path:filename>")
def uploaded_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


TRACK = """<!doctype html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>Track complaint #{{ row.id }}</title><style>body{font:16px Arial;background:#f1f5f9;color:#172554;margin:0;padding:20px}.box{max-width:650px;margin:35px auto;background:white;padding:25px;border-radius:12px}h1{color:#155e75}.steps{display:flex;gap:5px;margin:22px 0}.step{flex:1;padding:10px 5px;text-align:center;background:#e2e8f0;border-radius:6px;font-size:13px}.active{background:#0e7490;color:white}a{color:#0e7490}</style></head><body><main class='box'><h1>Complaint progress</h1><h2>Report #{{ row.id }}</h2><p><b>Category:</b> {{ row.category }} · <b>Department:</b> {{ row.department }}</p><p>{{ row.summary }}</p><div class='steps'>{% for status in statuses %}<div class='step {{ 'active' if status == row.status else '' }}'>{{ status }}</div>{% endfor %}</div><p><b>Current status:</b> {{ row.status }}</p><p>This page reflects the latest status saved by the city team. Keep this link to check again.</p><a href='/'>Submit another report</a></main></body></html>"""


@app.route("/complaints")
def complaints():
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
        stats = {"total": len(rows), "open": sum(row["status"] != "Resolved" for row in rows),
                 "high": sum(row["priority"] == "High" for row in rows),
                 "duplicates": sum(row["duplicate_of"] is not None for row in rows)}
        category_counts = {}
        status_counts = {}
        for row in rows:
            category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
            status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    map_rows = [{"id": row["id"], "location": row["location"], "category": row["category"],
                 "priority": row["priority"], "summary": row["summary"], "lat": row["latitude"], "lon": row["longitude"]}
                for row in rows if row["latitude"] is not None and row["longitude"] is not None]
    locations = {}
    for row in rows:
        if row["latitude"] is not None and row["longitude"] is not None:
            summary = locations.setdefault(row["location"], {"count": 0, "high": 0, "categories": {}})
            summary["count"] += 1
            summary["high"] += row["priority"] == "High"
            summary["categories"][row["category"]] = summary["categories"].get(row["category"], 0) + 1
    hotspots = sorted(locations.items(), key=lambda item: (item[1]["count"], item[1]["high"]), reverse=True)[:3]
    priority_reasons = {row["id"]: priority_reason(row["description"], row["priority"]) for row in rows}
    return render_template_string(DASHBOARD, rows=rows, stats=stats, categories=category_counts,
                                  statuses=status_counts, map_data=map_rows, all_statuses=STATUSES,
                                  departments=DEPARTMENTS, priority_reasons=priority_reasons, hotspots=hotspots)


@app.post("/complaints/<int:complaint_id>/update")
def update_complaint(complaint_id):
    status = request.form.get("status", "")
    department = request.form.get("department", "")
    if status in STATUSES and department in DEPARTMENTS:
        with connect_db() as conn:
            conn.execute("UPDATE complaints SET status=?, department=? WHERE id=?", (status, department, complaint_id))
    return redirect(url_for("complaints"))


DASHBOARD = """<!doctype html><html><head><title>CivicAI — Action dashboard</title><meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'><style>
*{box-sizing:border-box}body{font:15px Arial,sans-serif;background:#f1f5f9;margin:0;color:#172554}main{max-width:1200px;margin:28px auto;padding:0 18px}h1{color:#155e75}.top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.top a{color:#0e7490}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}.stat,.panel,.card{background:white;border-radius:11px;padding:17px;box-shadow:0 2px 12px #0000000b}.stat strong{display:block;font-size:25px;color:#0e7490;margin-top:5px}.grid{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin:16px 0}.panel h2{margin-top:0;font-size:19px}#map{height:350px;border-radius:8px}.bars div{padding:8px 0;border-bottom:1px solid #e2e8f0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:13px;margin-top:14px}.card h3{margin-top:0}.pill{display:inline-block;background:#e0f2fe;color:#075985;padding:4px 8px;border-radius:20px;font-size:12px}.high{background:#fee2e2;color:#991b1b}.duplicate{color:#9a3412}.summary{color:#475569}form{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}select,button{padding:8px;border:1px solid #cbd5e1;border-radius:6px;background:white}button{background:#0e7490;color:white;border:0;cursor:pointer}@media(max-width:760px){.grid{grid-template-columns:1fr}}</style></head>
<body><main><div class='top'><div><h1>CivicAI Action Dashboard</h1><p>Turn community reports into department action.</p></div><a href='/'>＋ Submit a complaint</a></div>
<section class='stats'><div class='stat'>All complaints<strong>{{ stats.total }}</strong></div><div class='stat'>Open<strong>{{ stats.open }}</strong></div><div class='stat'>High priority<strong>{{ stats.high }}</strong></div><div class='stat'>Possible duplicates<strong>{{ stats.duplicates }}</strong></div></section>
<section class='grid'><div class='panel'><h2>Complaint hotspots</h2><div id='map'></div><small>Map includes reports with supplied coordinates. Demo coordinates are fictional.</small><h2>Area patterns</h2><div class='bars'>{% for place,info in hotspots %}<div><b>{{ place }}</b>: {{ info.count }} reports · {{ info.high }} high priority</div>{% else %}<div>No coordinate clusters yet.</div>{% endfor %}</div></div><div class='panel'><h2>By category</h2><div class='bars'>{% for name,count in categories.items() %}<div>{{ name }} <b>{{ count }}</b></div>{% endfor %}</div><h2>Status</h2><div class='bars'>{% for name,count in statuses.items() %}<div>{{ name }} <b>{{ count }}</b></div>{% endfor %}</div><p><b>Action brief:</b> Review the highest-volume areas first, then prioritize high-risk hazards within those clusters. This is a count-based prototype insight.</p></div></section>
<h2>Complaints</h2><section class='cards'>{% for row in rows %}<article class='card'><h3>#{{ row.id }} — {{ row.category }}</h3><span class='pill {{ 'high' if row.priority == 'High' else '' }}'>{{ row.priority }} priority</span>{% if row.duplicate_of %}<span class='duplicate'> Possible duplicate of #{{ row.duplicate_of }}</span>{% endif %}
<p><b>Location:</b> {{ row.location }}</p>{% if row.category_hint != 'Not specified' %}<p><b>Citizen selected:</b> {{ row.category_hint }} · <b>Suggested:</b> {{ row.category }}</p>{% endif %}<p class='summary'><b>Summary:</b> {{ row.summary }}</p><p><b>Priority reason:</b> {{ priority_reasons[row.id] }}</p><p><b>Department:</b> {{ row.department }}</p><p><b>Submitted:</b> {{ row.created_at }} · <b>Status:</b> <a href='/track/{{ row.id }}'>{{ row.status }} · citizen tracking</a></p>{% if row.image_path %}<p><img src='/uploads/{{ row.image_path }}' alt='Citizen submitted photo' style='max-width:100%;border-radius:8px'></p>{% endif %}
<form method='post' action='/complaints/{{ row.id }}/update'><select name='department' aria-label='Department'>{% for dept in departments %}<option {{ 'selected' if dept == row.department else '' }}>{{ dept }}</option>{% endfor %}</select><select name='status' aria-label='Status'>{% for status in all_statuses %}<option {{ 'selected' if status == row.status else '' }}>{{ status }}</option>{% endfor %}</select><button>Save assignment</button></form></article>{% else %}<p>No complaints yet.</p>{% endfor %}</section></main>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script><script src='https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js'></script><script>const reports={{ map_data|tojson }};const map=L.map('map').setView([40.713,-74.006],13);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap contributors'}).addTo(map);if(reports.length){const points=reports.map(r=>[r.lat,r.lon]);L.heatLayer(reports.map(r=>[r.lat,r.lon,r.priority==='High'?1:.5]),{radius:28,blur:18}).addTo(map);reports.forEach(r=>{const popup=document.createElement('div');popup.style.whiteSpace='pre-line';popup.textContent='#'+r.id+' '+r.category+'\\n'+r.location+'\\n'+r.summary;L.circleMarker([r.lat,r.lon],{radius:r.priority==='High'?8:5,color:r.priority==='High'?'#dc2626':'#0284c7',fillOpacity:.45}).bindPopup(popup).addTo(map);});map.fitBounds(points,{padding:[25,25]});}</script></body></html>"""


# The app starts with `python3 app.py`; initializing here also supports `flask run`.
init_db()

if __name__ == "__main__":
    # macOS ControlCenter commonly reserves port 5000, so use 5001 by default.
    app.run(debug=True, port=5001)
