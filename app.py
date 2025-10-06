from flask import Flask, request, jsonify, session, redirect
import os, json
from datetime import datetime
from flask_cors import CORS
from GoogleCalendarSync import GoogleCalendarSync
from oop_events import CalendarManager  # tu clase con Event y CalendarManager
from google_auth_oauthlib.flow import Flow

# -------------------- CONFIG --------------------
sync = GoogleCalendarSync("credentials.json", "token.json")
calendar_manager = CalendarManager()  # maneja draft y real

app = Flask(__name__)
CORS(app)

app.secret_key = "secret"  # change

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_SECRETS_FILE = "credentials.json"

# -------------------- ENDPOINTS --------------------
@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/google/callback"
    )
    auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    session["state"] = state
    return redirect(auth_url)


@app.route("/auth/google/callback")
def auth_google_callback():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/google/callback"
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    # save token in file
    with open("token.json", "w") as token:
        token.write(creds.to_json())
    return "✅ Google Calendar connected"


@app.route("/google/events")
def google_events():
    sync = GoogleCalendarSync()
    service = sync.build_service()
    events_result = service.events().list(
        calendarId="primary", timeMin="2025-01-01T00:00:00Z", maxResults=50, singleEvents=True, orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])
    return jsonify(events)


@app.get("/events")
def get_events():
    """Returns all events (real + draft)"""
    real = [ev.to_dict() | {"draft": False} for ev in calendar_manager.real_calendar.events]
    draft = [ev.to_dict() | {"draft": True} for ev in calendar_manager.draft_calendar.events]
    
    # load google events
    service = sync.build_service()
    g_events_result = service.events().list(calendarId="primary").execute()
    g_events = []
    for e in g_events_result.get("items", []):
        start = e["start"].get("dateTime") or e["start"].get("date")
        end = e["end"].get("dateTime") or e["end"].get("date")
        
        # check if already in real_calendar (by summary + start)
        if any(ev.title == e.get("summary") and ev.start.isoformat() == start for ev in calendar_manager.real_calendar.events):
            continue  # skip duplicates

        g_events.append({
            "id": e.get("id"),
            "summary": e.get("summary"),
            "start": {"dateTime": start},
            "end": {"dateTime": end},
            "draft": False,
        })
    

    return jsonify(real + draft + g_events)


@app.post("/draft/add")
def add_event():
    """Adds event to draft"""
    data = request.json
    data = request.json
    title = data.get("title", "Untitled")
    start_dt = datetime.fromisoformat(data["start"])
    end_dt = datetime.fromisoformat(data["end"])
    duration = int((end_dt - start_dt).total_seconds() // 60)
    date = start_dt.strftime("%Y-%m-%d")
    start_time = start_dt.strftime("%H:%M")

    event = calendar_manager.create_event(
        date=date,
        start_time=start_time,
        duration_minutes=duration,
        title=title
    )
    calendar_manager.save_draft_event(event)
    return jsonify({"status": "ok"})


@app.post("/commit")
def commit():
    """Applies changes"""
    sync = GoogleCalendarSync()
    service = sync.build_service()
    calendar_manager.apply_changes(service)

    with open(calendar_manager.real_file, "w", encoding="utf-8") as f:
        json.dump([ev.to_dict() for ev in calendar_manager.real_calendar.events], f, indent=2, ensure_ascii=False)

    return jsonify({"status": "committed"})


@app.post("/discard")
def discard():
    """Borra todos los drafts"""
    calendar_manager.draft_calendar.clear()
    if os.path.exists(calendar_manager.draft_file):
        os.remove(calendar_manager.draft_file)
    return jsonify({"status": "discarded"})


@app.get("/preview")
def preview():
    """Devuelve preview de eventos y conflictos"""
    # eventos reales y draft
    real = [ev.to_dict() | {"draft": False, "conflict": False} for ev in calendar_manager.real_calendar.events]
    draft = [ev.to_dict() | {"draft": True, "conflict": False} for ev in calendar_manager.draft_calendar.events]

    # conflictos
    overlaps = calendar_manager.find_all_overlaps()
    for (e1, e2) in overlaps:
        # buscar los eventos completos por título y fuente y marcar conflicto
        for ev in real + draft:
            if (ev["summary"], "real" if not ev["draft"] else "draft") == e1 or \
               (ev["summary"], "real" if not ev["draft"] else "draft") == e2:
                ev["conflict"] = True

    return jsonify({
        "real": real,
        "draft": draft
    })


@app.get("/conflicts")
def conflicts():
    """Devuelve solo los conflictos"""
    overlaps = calendar_manager.find_all_overlaps()
    return jsonify(overlaps)


# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(port=8000, debug=True)
