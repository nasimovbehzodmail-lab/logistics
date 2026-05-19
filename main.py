from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import psycopg2.extras
from database import get_connection, init_db

app = FastAPI(title="Logistika - Mashina ro'yxati")

@app.on_event("startup")
def startup():
    init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

class VehicleCreate(BaseModel):
    plate_number: str
    model: str
    from_city: str
    to_city: str
    cargo_type: Optional[str] = None
    weight: Optional[float] = None
    client_price: int
    cost_price: int
    note: Optional[str] = None

@app.post("/api/vehicles")
def add_vehicle(v: VehicleCreate):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            INSERT INTO vehicles (plate_number, model, from_city, to_city, cargo_type, weight, client_price, cost_price, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (v.plate_number, v.model, v.from_city, v.to_city, v.cargo_type, v.weight, v.client_price, v.cost_price, v.note))
        row = dict(cur.fetchone())
        row["profit"] = row["client_price"] - row["cost_price"]
        conn.commit()
        return {"success": True, "vehicle": row}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/api/vehicles")
def get_vehicles():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM vehicles ORDER BY created_at DESC")
        rows = cur.fetchall()
        vehicles = []
        for r in rows:
            v = dict(r)
            v.pop("profit", None)
            vehicles.append(v)
        total_client = sum(v["client_price"] for v in vehicles)
        total_profit = sum(v["profit"] for v in vehicles)
        return {
            "vehicles": vehicles,
            "total_count": len(vehicles),
            "total_client_price": total_client,
            "total_profit": total_profit
        }
    finally:
        cur.close()
        conn.close()

@app.delete("/api/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Mashina topilmadi")
        conn.commit()
        return {"success": True}
    finally:
        cur.close()
        conn.close()