from flask import Flask, request, jsonify, session, redirect, send_from_directory
import os, json
from datetime import datetime
from flask_cors import CORS
from GoogleCalendarSync import GoogleCalendarSync
from oop_events import CalendarManager
from openAIAPI import CalendarAIClient
from google_auth_oauthlib.flow import Flow

# -------------------- CONFIG --------------------
sync = GoogleCalendarSync(
    scopes=["https://www.googleapis.com/auth/calendar"],
    credentials_file="credentials.json",
    token_file="token.json"
)
calendar_manager = CalendarManager()
calendar_manager.real_calendar.load_from_file(calendar_manager.real_file)
calendar_manager.draft_calendar.load_from_file(calendar_manager.draft_file)

# Initialize OpenAI client - REPLACE WITH YOUR API KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
ai_client = None

app = Flask(__name__)
CORS(app)
app.secret_key = "secret"  # change in production

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_SECRETS_FILE = "credentials.json"

# -------------------- HELPER FUNCTIONS --------------------
def sync_google_to_file():
    """Fetch Google Calendar events and save them to calendar_export.json"""
    try:
        service = sync.build_service()
        
        # Fetch events from Google Calendar
        events_result = service.events().list(
            calendarId="primary",
            timeMin="2019-01-01T00:00:00Z",  # Fetch all events from 2019 onwards
            maxResults=2500,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        
        google_events = events_result.get("items", [])
        
        # Convert to our format and save to file
        formatted_events = []
        for e in google_events:
            start = e["start"].get("dateTime") or e["start"].get("date")
            end = e["end"].get("dateTime") or e["end"].get("date")
            
            formatted_events.append({
                "summary": e.get("summary", "Untitled"),
                "start": {"dateTime": start, "timeZone": e["start"].get("timeZone", "Europe/Madrid")},
                "end": {"dateTime": end, "timeZone": e["end"].get("timeZone", "Europe/Madrid")},
                "draft": False
            })
        
        # Save to calendar_export.json
        with open(calendar_manager.real_file, "w", encoding="utf-8") as f:
            json.dump(formatted_events, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Synced {len(formatted_events)} events from Google Calendar to {calendar_manager.real_file}")
        
    except Exception as e:
        print(f"⚠️ Error syncing Google Calendar: {e}")

def get_ai_client():
    """Get or create AI client with current calendar data"""
    global ai_client
    
    # First, sync Google Calendar to file
    sync_google_to_file()
    
    # Reload calendar data to get latest events
    calendar_manager.real_calendar.load_from_file(calendar_manager.real_file)
    calendar_manager.draft_calendar.load_from_file(calendar_manager.draft_file)
    
    ai_client = CalendarAIClient(
        api_key=OPENAI_API_KEY,
        calendar_file=calendar_manager.real_file,
        delta_file="calendar_delta.json"
    )
    return ai_client

# -------------------- EXISTING ENDPOINTS --------------------

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
    """Returns all events (real + draft) and syncs Google Calendar to file"""
    # First, sync Google Calendar events to the real calendar file
    sync_google_to_file()
    
    # Reload the calendar manager to get updated events
    calendar_manager.real_calendar.load_from_file(calendar_manager.real_file)
    
    real = [ev.to_dict() | {"draft": False} for ev in calendar_manager.real_calendar.events]
    draft = [ev.to_dict() | {"draft": True} for ev in calendar_manager.draft_calendar.events]
    
    return jsonify(real + draft)


@app.post("/draft/add")
def add_event():
    """Adds event to draft"""
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
    """Deletes all drafts"""
    calendar_manager.draft_calendar.clear()
    if os.path.exists(calendar_manager.draft_file):
        os.remove(calendar_manager.draft_file)
    return jsonify({"status": "discarded"})


@app.get("/preview")
def preview():
    """Returns preview of events and conflicts"""
    real = [ev.to_dict() | {"draft": False, "conflict": False} for ev in calendar_manager.real_calendar.events]
    draft = [ev.to_dict() | {"draft": True, "conflict": False} for ev in calendar_manager.draft_calendar.events]

    overlaps = calendar_manager.find_all_overlaps()
    for (e1, e2) in overlaps:
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
    """Returns only conflicts"""
    overlaps = calendar_manager.find_all_overlaps()
    return jsonify(overlaps)


# -------------------- NEW AI ENDPOINTS --------------------

@app.post("/sync/google")
def sync_google_calendar():
    """Manually sync Google Calendar to calendar_export.json"""
    try:
        sync_google_to_file()
        calendar_manager.real_calendar.load_from_file(calendar_manager.real_file)
        return jsonify({
            "status": "success",
            "message": f"Synced {len(calendar_manager.real_calendar.events)} events",
            "event_count": len(calendar_manager.real_calendar.events)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/ai/chat")
def ai_chat():
    """
    Handle AI chat requests
    Expected JSON: {
        "message": "user query",
        "mode": "natural" or "json"
    }
    """
    try:
        data = request.json
        user_message = data.get("message", "")
        mode = data.get("mode", "natural")  # "natural" or "json"
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        ai = get_ai_client()
        
        if mode == "natural":
            # Get natural language response
            response = ai.summarize_calendar(user_message)
            return jsonify({
                "type": "natural",
                "response": response
            })
        
        elif mode == "json":
            # Get JSON delta response
            delta = ai.generate_calendar_delta(user_message)
            return jsonify({
                "type": "json",
                "response": delta,
                "preview": {
                    "add_count": len(delta.get("add", [])),
                    "update_count": len(delta.get("update", [])),
                    "delete_count": len(delta.get("delete", []))
                }
            })
        
        else:
            return jsonify({"error": "Invalid mode. Use 'natural' or 'json'"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/ai/apply-delta")
def apply_ai_delta():
    """
    Apply the AI-generated delta (from calendar_delta.json)
    """
    try:
        if not os.path.exists("calendar_delta.json"):
            return jsonify({"error": "No delta file found"}), 400
        
        sync_client = GoogleCalendarSync()
        service = sync_client.build_service()
        
        # Apply the delta
        sync_client.apply_delta(auto_delete=False)
        
        # Reload calendars
        calendar_manager.real_calendar.load_from_file(calendar_manager.real_file)
        
        return jsonify({"status": "success", "message": "AI changes applied"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(port=8000, debug=True)
