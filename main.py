from fastapi import FastAPI, Query, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from db import get_db, init_db
from typing import Optional

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

init_db()


@app.get("/health", response_class=PlainTextResponse)
def health():
    try:
        con = get_db()
        con.execute("SELECT 1")
        con.close()
        return "ok"
    except Exception:
        return PlainTextResponse("bad", status_code=500)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    con = get_db()
    entries = con.execute(
        "SELECT * FROM entries ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    con.close()
    return templates.TemplateResponse(
        "index.html", {"request": request, "entries": entries}
    )


@app.post("/add")
def add_entry(content: str = Form(...)):
    con = get_db()
    con.execute("INSERT INTO entries (content) VALUES (?)", (content,))
    con.commit()
    con.close()
    return RedirectResponse("/", status_code=303)


@app.post("/add_raw", response_class=PlainTextResponse)
def add_raw(content: str = Form(...)):
    con = get_db()
    con.execute("INSERT INTO entries(content) VALUES (?)", (content,))
    con.commit()
    con.close()
    return PlainTextResponse("", status_code=204)


# original search
# @app.get("/search", response_class=HTMLResponse)
# def search(request: Request, q: str = ""):
#     con = get_db()
#     results = []
#     if q:
#         results = con.execute(
#             "SELECT * FROM entries WHERE content LIKE ? ORDER BY created_at DESC LIMIT 20",
#             (f"%{q}%",),
#         ).fetchall()
#     con.close()
#     return templates.TemplateResponse(
#         "search.html", {"request": request, "results": results, "q": q}
#     )


# FTS5
@app.get("/search", response_class=HTMLResponse)
def search(
    request: Request, q: Optional[str] = Query(None, min_length=2, max_length=64)
):
    if not q:
        # render the search page with no results
        return templates.TemplateResponse(
            "search.html", {"request": request, "entries": [], "q": ""}
        )

    tokens = [t for t in q.split() if t]
    match = " ".join(f"{t}*" for t in tokens) if tokens else ""
    
    con = get_db()
    rows = con.execute(
        """
        SELECT e.id, e.content, e.created_at
        FROM entries_fts f
        JOIN entries e ON e.id = f.rowid
        WHERE f.entries_fts MATCH ?
        ORDER BY e.created_at DESC
        LIMIT 20
        """,
        (match,),
    ).fetchall()
    con.close()
    return templates.TemplateResponse(
        "search.html", {"request": request, "results": rows, "q": q}
    )
