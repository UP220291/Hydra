from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from contextlib import contextmanager
from zoneinfo import ZoneInfo
import sqlite3, os

app = FastAPI()

# FIX #12: ruta absoluta para que Railway no pierda el DB al cambiar CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "hydra.db")

# FIX #1: timezone configurable por variable de entorno (default América/México)
TZ_NAME = os.getenv("APP_TIMEZONE", "America/Mexico_City")
TZ = ZoneInfo(TZ_NAME)

def now_local() -> datetime:
    return datetime.now(TZ)

def today_local() -> date:
    return now_local().date()

# FIX #6: context manager para conexiones, garantiza cierre siempre
@contextmanager
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at TEXT NOT NULL,
                amount TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                icon TEXT NOT NULL,
                day_required INTEGER NOT NULL,
                redeemed INTEGER DEFAULT 0,
                custom INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        existing = c.execute("SELECT COUNT(*) FROM rewards").fetchone()[0]
        if existing == 0:
            defaults = [
                ("Un beso",        "💋", 10, 0, 0),
                ("Carta de amor",  "💌", 20, 0, 0),
                ("Salida a cenar", "🍽️", 30, 0, 0),
                ("Sorpresa",       "✨", 40, 0, 0),
            ]
            c.executemany(
                "INSERT INTO rewards (name, icon, day_required, redeemed, custom) VALUES (?,?,?,?,?)",
                defaults
            )
        c.execute("INSERT OR IGNORE INTO settings VALUES ('outfit', 'classic')")
        conn.commit()

init_db()

# ── helpers ──────────────────────────────────────────────────────────────────

def compute_streak() -> int:
    """
    FIX #1: computa racha usando la zona horaria local configurada,
    no UTC del servidor.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date(logged_at) as d FROM logs ORDER BY d DESC"
        ).fetchall()
    if not rows:
        return 0
    streak = 0
    today = today_local()
    for i, row in enumerate(rows):
        expected = today - timedelta(days=i)
        if row["d"] == str(expected):
            streak += 1
        else:
            break
    return streak

def flame_level(streak: int) -> int:
    thresholds = [3, 7, 14, 21, 30]
    for lvl, t in enumerate(thresholds, 1):
        if streak < t:
            return lvl
    return 6

VALID_AMOUNTS = {"trago", "vaso", "botella"}
VALID_OUTFITS = {"classic": 0, "crown": 14, "flowers": 21, "rainbow": 30, "space": 45, "angel": 60}

# ── models ───────────────────────────────────────────────────────────────────

class LogIn(BaseModel):
    amount: str

class RewardIn(BaseModel):
    name: str
    icon: str
    day_required: int

class OutfitIn(BaseModel):
    outfit: str

# ── routes ───────────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    streak = compute_streak()
    level  = flame_level(streak)
    today  = str(today_local())
    with get_db() as conn:
        today_logs = conn.execute(
            "SELECT amount FROM logs WHERE date(logged_at) = ? ORDER BY logged_at DESC",
            (today,)
        ).fetchall()
        outfit = conn.execute("SELECT value FROM settings WHERE key='outfit'").fetchone()
    return {
        "streak": streak,
        "level": level,
        "today_logs": [r["amount"] for r in today_logs],
        "outfit": outfit["value"] if outfit else "classic",
    }

@app.post("/api/log")
def log_water(body: LogIn):
    if body.amount not in VALID_AMOUNTS:
        raise HTTPException(400, f"amount inválido. Usa: {', '.join(VALID_AMOUNTS)}")
    ts = now_local().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO logs (logged_at, amount) VALUES (?, ?)",
            (ts, body.amount)
        )
        conn.commit()
    streak = compute_streak()
    return {"ok": True, "streak": streak, "level": flame_level(streak)}

@app.get("/api/rewards")
def get_rewards():
    streak = compute_streak()
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM rewards ORDER BY day_required").fetchall()
    return {
        "rewards": [
            {
                "id":           r["id"],
                "name":         r["name"],
                "icon":         r["icon"],
                "day_required": r["day_required"],
                "redeemed":     bool(r["redeemed"]),
                "custom":       bool(r["custom"]),
                "unlocked":     streak >= r["day_required"],
            }
            for r in rows
        ],
        "streak": streak,
    }

@app.post("/api/rewards/{reward_id}/redeem")
def redeem_reward(reward_id: int):
    streak = compute_streak()
    with get_db() as conn:
        reward = conn.execute("SELECT * FROM rewards WHERE id=?", (reward_id,)).fetchone()
        if not reward:
            raise HTTPException(404, "Premio no encontrado")
        if streak < reward["day_required"]:
            raise HTTPException(403, "Racha insuficiente")
        conn.execute("UPDATE rewards SET redeemed=1 WHERE id=?", (reward_id,))
        conn.commit()
    return {"ok": True}

@app.post("/api/rewards")
def add_reward(body: RewardIn):
    if not body.name.strip():
        raise HTTPException(400, "El nombre no puede estar vacío")
    if body.day_required < 1:
        raise HTTPException(400, "day_required debe ser >= 1")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO rewards (name, icon, day_required, custom) VALUES (?,?,?,1)",
            (body.name.strip(), body.icon, body.day_required)
        )
        conn.commit()
    return {"ok": True}

@app.delete("/api/rewards/{reward_id}")
def delete_reward(reward_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM rewards WHERE id=? AND custom=1", (reward_id,))
        conn.commit()
    return {"ok": True}

@app.post("/api/outfit")
def set_outfit(body: OutfitIn):
    req = VALID_OUTFITS.get(body.outfit)
    if req is None:
        raise HTTPException(400, "Outfit inválido")
    streak = compute_streak()
    if streak < req:
        raise HTTPException(403, f"Necesitas {req} días de racha para este outfit")
    with get_db() as conn:
        conn.execute("UPDATE settings SET value=? WHERE key='outfit'", (body.outfit,))
        conn.commit()
    return {"ok": True}

@app.get("/api/history")
def get_history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT date(logged_at) as d, COUNT(*) as total, GROUP_CONCAT(amount) as amounts "
            "FROM logs GROUP BY date(logged_at) ORDER BY d DESC LIMIT 30"
        ).fetchall()
    return {"history": [dict(r) for r in rows]}

# ── static / PWA ─────────────────────────────────────────────────────────────
# FIX #2: mount ANTES de la catch-all, y la catch-all explícita en último lugar

@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(BASE_DIR, "static", "manifest.json"))

@app.get("/sw.js")
def sw():
    return FileResponse(
        os.path.join(BASE_DIR, "static", "sw.js"),
        media_type="application/javascript"
    )

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/{full_path:path}")
def spa(full_path: str):
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))
