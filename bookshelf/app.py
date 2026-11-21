import hmac
import secrets
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from threading import Event, Thread
from time import monotonic
from uuid import uuid4

from flask import Flask, abort, flash, redirect, render_template, request, send_file, session, url_for
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from werkzeug.security import check_password_hash

from .tts import GenerationError, generate


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, language TEXT NOT NULL, pages INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY, book_id TEXT NOT NULL REFERENCES books(id),
    first_page INTEGER NOT NULL, last_page INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued', error TEXT
);
"""


@contextmanager
def database(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def claim_job(db_path):
    with database(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        job = db.execute("""
            SELECT clips.*, books.language FROM clips JOIN books ON books.id = clips.book_id
            WHERE state = 'queued' ORDER BY clips.rowid LIMIT 1
        """).fetchone()
        if job:
            db.execute("UPDATE clips SET state = 'running' WHERE id = ?", (job["id"],))
    return job


def run_job(root, config, logger, render=generate):
    db_path = root / "library.sqlite3"
    job = claim_job(db_path)
    if job is None:
        return False

    try:
        render(
            root / "books" / f"{job['book_id']}.pdf",
            job["first_page"], job["last_page"], job["language"],
            root / "audio" / f"{job['id']}.mp3",
            region=config["region"], key=config["minimax_key"],
        )
        state, error = "ready", None
    except GenerationError as exc:
        state, error = "failed", str(exc)
    except Exception:
        logger.error("Generation failed for clip %s", job["id"])
        state, error = "failed", "生成音频时遇到错误。请重试，或换一个 PDF 页码范围。"

    with database(db_path) as db:
        db.execute("UPDATE clips SET state = ?, error = ? WHERE id = ?", (state, error, job["id"]))
    return True


def recover_jobs(root):
    with database(root / "library.sqlite3") as db:
        for job in db.execute("SELECT id FROM clips WHERE state = 'running'").fetchall():
            path = root / "audio" / f"{job['id']}.mp3"
            state, error = ("ready", None) if path.is_file() and path.stat().st_size else (
                "failed", "上次生成被应用重启中断。请重试。"
            )
            db.execute("UPDATE clips SET state = ?, error = ? WHERE id = ?", (state, error, job["id"]))


def start_worker(app, root, config):
    recover_jobs(root)
    wake = app.extensions["jobs_ready"]

    def loop():
        while True:
            try:
                if run_job(root, config, app.logger):
                    continue
            except sqlite3.Error:
                app.logger.error("Unable to access the generation queue")
            wake.wait(1)
            wake.clear()

    Thread(target=loop, daemon=True, name="audiobook-generator").start()


def create_app(root, credentials, *, secure=True):
    root = Path(root).resolve()
    for directory in ("books", "audio"):
        (root / directory).mkdir(mode=0o700, parents=True, exist_ok=True)
    db_path = root / "library.sqlite3"
    with database(db_path) as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript(SCHEMA)

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=credentials["session_key"],
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=secure,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    )
    wake = app.extensions["jobs_ready"] = Event()
    login_window = []

    @app.before_request
    def authorize():
        if request.endpoint is None or request.endpoint == "static":
            return
        if request.endpoint != "login" and not session.get("owner"):
            if request.method == "GET":
                session["return_to"] = url_for(request.endpoint, **request.view_args)
            return redirect(url_for("login"))
        if request.method == "POST":
            expected = session.get("csrf", "")
            given = request.form.get("csrf", "")
            if not expected or not hmac.compare_digest(expected.encode(), given.encode()):
                abort(400)

    @app.context_processor
    def forms():
        return {"csrf": session.setdefault("csrf", secrets.token_hex(24))}

    @app.after_request
    def private(response):
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("page.html", view="error", error="文件太大，请上传小于 50 MB 的 PDF。"), 413

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return redirect(url_for("library")) if session.get("owner") else render_template("page.html", view="login")
        now = monotonic()
        login_window[:] = [stamp for stamp in login_window if now - stamp < 60]
        if len(login_window) >= 8:
            return render_template("page.html", view="login", error="尝试次数较多，请等一分钟再试。"), 429
        password = request.form.get("password", "")
        if len(password) > 1024 or not check_password_hash(credentials["password_hash"], password):
            login_window.append(now)
            return render_template("page.html", view="login", error="密码不正确。"), 401
        login_window.clear()
        destination = session.get("return_to", url_for("library"))
        session.clear()
        session.permanent = True
        session["owner"] = True
        return redirect(destination, code=303)

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"), code=303)

    @app.get("/")
    def library():
        with database(db_path) as db:
            books = db.execute("SELECT * FROM books ORDER BY rowid DESC").fetchall()
            current = db.execute("SELECT value FROM settings WHERE name = 'current_book'").fetchone()
        return render_template("page.html", view="library", books=books, current=current["value"] if current else None)

    @app.post("/books")
    def upload():
        pdf = request.files.get("pdf")
        language = request.form.get("language")
        if not pdf or not pdf.filename or language not in {"zh", "en"}:
            flash("请选择 PDF 和语言。")
            return redirect(url_for("library"), code=303)
        filename = pdf.filename.replace("\\", "/").split("/")[-1]
        title = (request.form.get("title", "").strip() or Path(filename).stem)[:150]
        book_id = uuid4().hex
        destination = root / "books" / f"{book_id}.pdf"
        try:
            with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
                candidate = Path(folder) / "upload.pdf"
                pdf.save(candidate)
                with candidate.open("rb") as handle:
                    if handle.read(5) != b"%PDF-":
                        raise ValueError("invalid PDF")
                    reader = PdfReader(handle)
                    if reader.is_encrypted or not len(reader.pages):
                        raise ValueError("unsupported PDF")
                    pages = len(reader.pages)
                candidate.replace(destination)
            try:
                with database(db_path) as db:
                    db.execute("INSERT INTO books VALUES (?, ?, ?, ?)", (book_id, title or "未命名书籍", language, pages))
                    db.execute("INSERT OR IGNORE INTO settings VALUES ('current_book', ?)", (book_id,))
            except sqlite3.Error:
                destination.unlink(missing_ok=True)
                raise
        except (ValueError, PyPdfError):
            flash("无法读取这份 PDF。请上传未加密、有文字层的 PDF。")
            return redirect(url_for("library"), code=303)
        return redirect(url_for("book", book_id=book_id), code=303)

    def get_book(db, book_id):
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            abort(404)
        return row

    def get_clip(db, clip_id):
        row = db.execute("""
            SELECT clips.*, books.title, books.language FROM clips JOIN books ON books.id = clips.book_id
            WHERE clips.id = ?
        """, (clip_id,)).fetchone()
        if row is None:
            abort(404)
        return row

    @app.get("/books/<book_id>")
    def book(book_id):
        with database(db_path) as db:
            item = get_book(db, book_id)
            clips = db.execute("SELECT * FROM clips WHERE book_id = ? ORDER BY rowid DESC", (book_id,)).fetchall()
            current = db.execute("SELECT value FROM settings WHERE name = 'current_book'").fetchone()
        return render_template("page.html", view="book", book=item, clips=clips, is_current=bool(current and current["value"] == book_id))

    @app.post("/books/<book_id>/current")
    def select_book(book_id):
        with database(db_path) as db:
            get_book(db, book_id)
            db.execute("INSERT OR REPLACE INTO settings VALUES ('current_book', ?)", (book_id,))
        return redirect(url_for("book", book_id=book_id), code=303)

    @app.post("/books/<book_id>/clips")
    def create_clip(book_id):
        with database(db_path) as db:
            item = get_book(db, book_id)
            try:
                first = int(request.form.get("first_page", ""))
                last = int(request.form.get("last_page") or first)
                if not 1 <= first <= last <= item["pages"]:
                    raise ValueError("out of range")
            except ValueError:
                flash(f"输入有效的起止页码。此 PDF 有 {item['pages']} 页。")
                return redirect(url_for("book", book_id=book_id), code=303)
            clip_id = uuid4().hex
            db.execute(
                "INSERT INTO clips (id, book_id, first_page, last_page) VALUES (?, ?, ?, ?)",
                (clip_id, book_id, first, last),
            )
        wake.set()
        return redirect(url_for("clip", clip_id=clip_id), code=303)

    @app.get("/clips/<clip_id>")
    def clip(clip_id):
        with database(db_path) as db:
            item = get_clip(db, clip_id)
        return render_template("page.html", view="clip", clip=item)

    @app.post("/clips/<clip_id>/retry")
    def retry(clip_id):
        with database(db_path) as db:
            get_clip(db, clip_id)
            db.execute("UPDATE clips SET state = 'queued', error = NULL WHERE id = ? AND state = 'failed'", (clip_id,))
        wake.set()
        return redirect(url_for("clip", clip_id=clip_id), code=303)

    @app.get("/clips/<clip_id>/audio")
    def audio(clip_id):
        with database(db_path) as db:
            item = get_clip(db, clip_id)
        path = root / "audio" / f"{item['id']}.mp3"
        if item["state"] != "ready" or not path.is_file():
            abort(404)
        return send_file(path, mimetype="audio/mpeg", conditional=True)

    return app
