from flask import Flask, request, jsonify
import os, json, datetime
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
    """Añade un evento al calendario draft"""
    data = request.json
    # calcular duración en minutos si se dan start y end completos
    if "end" in data:
        start_dt = datetime.fromisoformat(data["start"])
        end_dt = datetime.fromisoformat(data["end"])
        duration = int((end_dt - start_dt).total_seconds() // 60)
        start_time = start_dt.strftime("%H:%M")
        date = start_dt.strftime("%Y-%m-%d")
    else:
        date = data["start"][:10]
        start_time = data["start"][11:16]
        duration = data.get("duration", 60)  # default 1 hora

    event = calendar_manager.create_event(
        date=date,
        start_time=start_time,
        duration_minutes=duration,
        title=data["summary"]
    )
    calendar_manager.save_draft_event(event)
    return jsonify({"status": "ok"})


@app.post("/commit")
def commit():
    """Aplica los cambios: sube drafts a Google Calendar y los mueve a real"""
    calendar_manager.apply_changes(sync.service)

    # guardar real localmente
    all_real = [ev.to_dict() for ev in calendar_manager.real_calendar.events]
    if os.path.exists(calendar_manager.real_file):
        try:
            with open(calendar_manager.real_file, "r", encoding="utf-8") as f:
                old_real = json.load(f)
        except json.JSONDecodeError:
            old_real = []
    else:
        old_real = []

    all_real = old_real + all_real
    with open(calendar_manager.real_file, "w", encoding="utf-8") as f:
        json.dump(all_real, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "committed"})


@app.post("/discard")
def discard():
    """Borra todos los drafts"""
    calendar_manager.draft_calendar.clear()
    if os.path.exists(calendar_manager.draft_calendar.source):
        os.remove(calendar_manager.draft_file)
    return jsonify({"status": "discarded"})


@app.get("/preview")
def preview():
    """Devuelve preview de eventos y conflictos"""
    real = [ev.to_dict() | {"draft": False} for ev in calendar_manager.real_calendar.events]
    draft = [ev.to_dict() | {"draft": True} for ev in calendar_manager.draft_calendar.events]
    conflicts = calendar_manager.find_all_overlaps()
    return jsonify({
        "real": real,
        "draft": draft,
        "conflicts": conflicts
    })


@app.get("/conflicts")
def conflicts():
    """Devuelve solo los conflictos"""
    overlaps = calendar_manager.find_all_overlaps()
    return jsonify(overlaps)


# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(port=8000, debug=True)
