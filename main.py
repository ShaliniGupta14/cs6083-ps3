from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import psycopg2
import psycopg2.extras
from datetime import date

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ── DB connection ────────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        dbname="flights_db",
        user="shalinigupta"
        # No host = uses Unix socket (correct for Homebrew PostgreSQL on Mac)
    )

# ── Home: search form ────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ── Part (b): search results ─────────────────────────────────────────────────
@app.post("/flights", response_class=HTMLResponse)
def search_flights(
    request: Request,
    origin: str = Form(...),
    dest:   str = Form(...),
    date_from: date = Form(...),
    date_to:   date = Form(...)
):
    sql = """
        SELECT
            f.flight_number,
            f.departure_date,
            fs.origin_code,
            fs.dest_code,
            fs.departure_time,
            fs.duration,
            fs.airline_name
        FROM Flight f
        JOIN FlightService fs ON f.flight_number = fs.flight_number
        WHERE fs.origin_code  = %(origin)s
          AND fs.dest_code    = %(dest)s
          AND f.departure_date BETWEEN %(date_from)s AND %(date_to)s
        ORDER BY f.departure_date, fs.departure_time
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, {"origin": origin.upper(), "dest": dest.upper(),
                              "date_from": date_from, "date_to": date_to})
            flights = cur.fetchall()

    return templates.TemplateResponse("flights.html", {
        "request": request,
        "flights": flights,
        "origin": origin.upper(),
        "dest":   dest.upper(),
        "date_from": date_from,
        "date_to":   date_to,
    })

# ── Part (c): seat availability for a specific flight + date ─────────────────
@app.get("/flight/{flight_number}/{departure_date}", response_class=HTMLResponse)
def flight_detail(request: Request, flight_number: str, departure_date: date):
    sql = """
        SELECT
            f.flight_number,
            f.departure_date,
            fs.origin_code,
            fs.dest_code,
            fs.departure_time,
            fs.airline_name,
            a.capacity,
            COUNT(b.pid) AS booked,
            a.capacity - COUNT(b.pid) AS available
        FROM Flight f
        JOIN FlightService fs ON f.flight_number = fs.flight_number
        JOIN Aircraft      a  ON f.plane_type    = a.plane_type
        LEFT JOIN Booking  b  ON b.flight_number   = f.flight_number
                              AND b.departure_date  = f.departure_date
        WHERE f.flight_number  = %(fn)s
          AND f.departure_date = %(dd)s
        GROUP BY f.flight_number, f.departure_date,
                 fs.origin_code, fs.dest_code,
                 fs.departure_time, fs.airline_name, a.capacity
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, {"fn": flight_number, "dd": departure_date})
            detail = cur.fetchone()

    return templates.TemplateResponse("detail.html", {
        "request": request,
        "flight":  detail,
    })