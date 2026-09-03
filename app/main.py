import os
import time
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel

DB_DSN = os.getenv("DATABASE_URL", "postgresql://secureuser:change_me@db:5432/securecloud")

REQUEST_COUNT = Counter(
    "securecloud_http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "securecloud_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


def get_conn():
    return psycopg.connect(DB_DSN)


def init_db():
    last_error = None
    for _ in range(20):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS notes (
                            id SERIAL PRIMARY KEY,
                            content VARCHAR(500) NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        )
                        """
                    )
                conn.commit()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"Database unavailable: {last_error}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="SecureCloudLab API", version="1.0.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())


class NoteIn(BaseModel):
    content: str


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        REQUEST_COUNT.labels("GET", "/health", "200").inc()
        return {"status": "ok", "database": "reachable"}
    except Exception as exc:
        REQUEST_COUNT.labels("GET", "/health", "503").inc()
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/notes")
def list_notes():
    with REQUEST_LATENCY.labels("GET", "/api/notes").time():
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, content, created_at FROM notes ORDER BY id DESC")
                rows = cur.fetchall()
        REQUEST_COUNT.labels("GET", "/api/notes", "200").inc()
        return [
            {"id": row[0], "content": row[1], "created_at": row[2]}
            for row in rows
        ]


@app.post("/api/notes", status_code=201)
def create_note(note: NoteIn):
    content = note.content.strip()
    if not content:
        REQUEST_COUNT.labels("POST", "/api/notes", "400").inc()
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    if len(content) > 500:
        REQUEST_COUNT.labels("POST", "/api/notes", "400").inc()
        raise HTTPException(status_code=400, detail="Content too long")

    with REQUEST_LATENCY.labels("POST", "/api/notes").time():
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO notes(content) VALUES (%s) RETURNING id, content, created_at",
                    (content,),
                )
                row = cur.fetchone()
            conn.commit()
    REQUEST_COUNT.labels("POST", "/api/notes", "201").inc()
    return {"id": row[0], "content": row[1], "created_at": row[2]}
