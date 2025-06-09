from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Product(BaseModel):
    name: str
    store: str
    url: str
    stock_status: str
    last_alert_time: str
    price: Optional[str] = None
    image: Optional[str] = None
    variant: Optional[str] = None

@app.get("/products", response_model=List[Product])
def get_products():
    conn = sqlite3.connect("pokemon_scraper.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, store, url, stock_status, last_alert_time, price, image, variant FROM products")
    rows = cursor.fetchall()
    conn.close()
    return [Product(
        name=row[0],
        store=row[1],
        url=row[2],
        stock_status=row[3],
        last_alert_time=row[4],
        price=row[5],
        image=row[6],
        variant=row[7],
    ) for row in rows]
