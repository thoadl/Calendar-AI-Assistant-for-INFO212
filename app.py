from flask import Flask, request, jsonify
import os, json
from datetime import datetime
from flask_cors import CORS
from GoogleCalendarSync import GoogleCalendarSync
from oop_events import CalendarManager  # tu clase con Event y CalendarManager

# -------------------- CONFIG --------------------
sync = GoogleCalendarSync("credentials.json", "token.json")
calendar_manager = CalendarManager()  # maneja draft y real

app = Flask(__name__)
CORS(app)

# -------------------- ENDPOINTS --------------------
@app.get("/events")
def get_events():
    """Devuelve todos los eventos (reales + draft)"""
    real = [ev.to_dict() | {"draft": False} for ev in calendar_manager.real_calendar.events]
    draft = [ev.to_dict() | {"draft": True} for ev in calendar_manager.draft_calendar.events]
    return jsonify(real + draft)


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
    calendar_manager.apply_changes(sync.service)

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
