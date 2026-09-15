import os
import re
import secrets
import sqlite3
import time
from collections import deque
from contextlib import contextmanager
from datetime import timedelta
from functools import wraps
from pathlib import Path
from threading import Lock

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "memo.db"))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=64 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "1") != "0",
)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MAX_TITLE_LENGTH = 120
MAX_CONTENT_LENGTH = 10_000
MAX_NOTES_PER_USER = 100
MAX_USER_STORAGE_BYTES = 1024 * 1024
LOGIN_WINDOW_SECONDS = 5 * 60
LOGIN_MAX_ATTEMPTS = 10
MAX_RATE_LIMIT_BUCKETS = 4096
login_attempts = {}
login_attempts_lock = Lock()
DUMMY_PASSWORD_HASH = generate_password_hash("timing-check-only-password")

PAGE = """
<!doctype html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} · Boblink Memo</title>
    <style nonce="{{ g.csp_nonce }}">
        :root {
            color-scheme: dark;
            --canvas: #0d1117;
            --surface: #161b22;
            --surface-subtle: #21262d;
            --border: #30363d;
            --border-muted: #21262d;
            --text: #f0f6fc;
            --text-muted: #8b949e;
            --accent: #2f81f7;
            --accent-hover: #58a6ff;
            --success: #238636;
            --success-hover: #2ea043;
            --danger-bg: rgba(248, 81, 73, 0.1);
            --danger-border: rgba(248, 81, 73, 0.4);
            --success-bg: rgba(46, 160, 67, 0.1);
            --success-border: rgba(46, 160, 67, 0.4);
            --focus: rgba(88, 166, 255, 0.35);
        }

        * { box-sizing: border-box; }

        body {
            min-height: 100vh;
            margin: 0;
            background: var(--canvas);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 14px;
            line-height: 1.5;
        }

        a { color: var(--accent-hover); text-decoration: none; }
        a:hover { text-decoration: underline; }

        a:focus-visible,
        button:focus-visible,
        input:focus-visible,
        textarea:focus-visible {
            outline: 2px solid var(--accent-hover);
            outline-offset: 2px;
        }

        .page-shell {
            width: min(100% - 32px, 440px);
            margin: 0 auto;
            padding: 64px 0;
        }

        .page-shell-wide { width: min(100% - 32px, 960px); }

        .site-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 28px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text);
            font-size: 20px;
            font-weight: 650;
            letter-spacing: -0.02em;
        }

        .brand:hover { text-decoration: none; }

        .brand-mark {
            display: grid;
            width: 34px;
            height: 34px;
            place-items: center;
            border: 1px solid var(--border);
            border-radius: 50%;
            background: var(--surface);
            color: var(--accent-hover);
            font-size: 16px;
        }

        .card {
            overflow: hidden;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface);
            box-shadow: 0 8px 24px rgba(1, 4, 9, 0.35);
        }

        .card-header { padding: 24px 24px 0; }

        .eyebrow {
            margin: 0 0 5px;
            color: var(--text-muted);
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.025em;
        }

        .card-body { padding: 24px; }

        .flash-list {
            margin: 20px 24px 0;
            padding: 0;
            list-style: none;
        }

        .flash-message {
            padding: 10px 12px;
            border: 1px solid var(--danger-border);
            border-radius: 6px;
            background: var(--danger-bg);
        }

        .flash-success {
            border-color: var(--success-border);
            background: var(--success-bg);
        }

        .flash-info {
            border-color: rgba(47, 129, 247, 0.4);
            background: rgba(47, 129, 247, 0.1);
        }

        .field { margin: 0 0 16px; }

        label {
            display: block;
            margin-bottom: 7px;
            font-weight: 600;
        }

        input {
            display: block;
            width: 100%;
            min-height: 38px;
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--canvas);
            color: var(--text);
            font: inherit;
            transition: border-color 120ms ease, box-shadow 120ms ease;
        }

        input:hover { border-color: #484f58; }

        input:focus {
            border-color: var(--accent-hover);
            outline: none;
            box-shadow: 0 0 0 3px var(--focus);
        }

        button,
        .button {
            display: inline-flex;
            min-height: 38px;
            align-items: center;
            justify-content: center;
            padding: 8px 16px;
            border: 1px solid rgba(240, 246, 252, 0.1);
            border-radius: 6px;
            background: var(--success);
            color: #fff;
            font: inherit;
            font-weight: 600;
            cursor: pointer;
            transition: background 120ms ease, border-color 120ms ease;
        }

        button:hover,
        .button:hover {
            background: var(--success-hover);
            text-decoration: none;
        }

        .button-block { width: 100%; }

        .button-secondary {
            border-color: var(--border);
            background: var(--surface-subtle);
            color: var(--text);
        }

        .button-secondary:hover {
            border-color: #8b949e;
            background: #30363d;
        }

        .auth-switch {
            margin: 16px 0 0;
            color: var(--text-muted);
            text-align: center;
        }

        .welcome {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 22px;
        }

        .avatar {
            display: grid;
            flex: 0 0 auto;
            width: 44px;
            height: 44px;
            place-items: center;
            border: 1px solid var(--border);
            border-radius: 50%;
            background: var(--surface-subtle);
            color: var(--accent-hover);
            font-size: 18px;
            font-weight: 700;
        }

        .welcome-title { margin: 0 0 2px; font-size: 16px; font-weight: 600; }
        .welcome-copy { margin: 0; color: var(--text-muted); }

        .divider {
            height: 1px;
            margin: 22px 0;
            border: 0;
            background: var(--border-muted);
        }

        .header-actions,
        .memo-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .inline-form { margin: 0; }

        .nav-link {
            display: inline-flex;
            min-height: 34px;
            align-items: center;
            padding: 6px 10px;
            border: 1px solid transparent;
            border-radius: 6px;
            color: var(--text-muted);
            font-weight: 600;
        }

        .nav-link:hover {
            border-color: var(--border);
            background: var(--surface);
            color: var(--text);
            text-decoration: none;
        }

        .button-danger { background: #b62324; }
        .button-danger:hover { background: #d1242f; }

        textarea {
            display: block;
            width: 100%;
            min-height: 260px;
            resize: vertical;
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--canvas);
            color: var(--text);
            font: inherit;
            line-height: 1.6;
        }

        textarea:focus {
            border-color: var(--accent-hover);
            outline: none;
            box-shadow: 0 0 0 3px var(--focus);
        }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 20px;
        }

        .section-header p { margin: 4px 0 0; color: var(--text-muted); }

        .memo-list {
            display: grid;
            gap: 12px;
            margin: 0;
            padding: 0;
            list-style: none;
        }

        .memo-item {
            display: block;
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--canvas);
            color: var(--text);
        }

        .memo-item:hover {
            border-color: var(--accent);
            text-decoration: none;
        }

        .memo-title { margin: 0 0 6px; font-size: 16px; font-weight: 600; }
        .memo-preview { margin: 0 0 10px; color: var(--text-muted); }
        .memo-meta { color: var(--text-muted); font-size: 12px; }

        .empty-state {
            padding: 48px 20px;
            border: 1px dashed var(--border);
            border-radius: 6px;
            color: var(--text-muted);
            text-align: center;
        }

        .note-content {
            min-height: 180px;
            margin: 0;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            color: var(--text);
            font-family: inherit;
        }

        .data-table { width: 100%; border-collapse: collapse; }
        .data-table th, .data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            text-align: left;
        }
        .data-table th { color: var(--text-muted); font-size: 12px; }
        .table-wrap { overflow-x: auto; }
        .badge {
            display: inline-block;
            padding: 2px 7px;
            border: 1px solid var(--border);
            border-radius: 999px;
            color: var(--text-muted);
            font-size: 12px;
        }
        .badge-admin { border-color: var(--success-border); color: #3fb950; }

        @media (max-width: 520px) {
            .page-shell { width: min(100% - 24px, 440px); padding: 32px 0; }
            .card-header, .card-body { padding-right: 20px; padding-left: 20px; }
            .flash-list { margin-right: 20px; margin-left: 20px; }
            .site-header, .section-header { align-items: flex-start; flex-direction: column; }
            .header-actions { width: 100%; flex-wrap: wrap; }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { transition: none !important; }
        }
    </style>
</head>
<body>
    <main class="page-shell{% if wide %} page-shell-wide{% endif %}">
        <header class="site-header">
            <a class="brand" href="{{ url_for('index') }}" aria-label="Boblink Memo 홈">
                <span class="brand-mark" aria-hidden="true">B</span>
                <span>Boblink Memo</span>
            </a>
            {% if g.user %}
                <nav class="header-actions" aria-label="주요 메뉴">
                    <a class="nav-link" href="{{ url_for('index') }}">내 메모</a>
                    {% if g.user['is_admin'] %}
                        <a class="nav-link" href="{{ url_for('admin_users') }}">관리자</a>
                    {% endif %}
                    <form class="inline-form" method="post" action="{{ url_for('logout') }}">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                        <button class="button-secondary" type="submit">로그아웃</button>
                    </form>
                </nav>
            {% endif %}
        </header>

        <section class="card" aria-labelledby="page-title">
            <header class="card-header">
                <p class="eyebrow">Simple, private notes</p>
                <h1 id="page-title">{{ title }}</h1>
            </header>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <ul class="flash-list" role="status">
                        {% for category, message in messages %}
                            <li class="flash-message flash-{{ category }}">{{ message }}</li>
                        {% endfor %}
                    </ul>
                {% endif %}
            {% endwith %}

            <div class="card-body">{{ content|safe }}</div>
        </section>
    </main>
</body>
</html>
"""


@contextmanager
def get_db():
    connection = sqlite3.connect(DATABASE, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(users)")
        }
        if "is_admin" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0"
            )
        if "created_at" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
            connection.execute(
                "UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
                content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 10000),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_notes_user_updated "
            "ON notes (user_id, updated_at DESC, id DESC)"
        )


def bootstrap_admin():
    password = os.environ.get("ADMIN_PASSWORD")
    flag = os.environ.get("CTF_FLAG")
    if not password:
        return
    if not 16 <= len(password) <= 128:
        raise RuntimeError("ADMIN_PASSWORD must contain 16 to 128 characters.")
    if flag and not re.fullmatch(r"SBOB\{[^{}]{8,128}\}", flag):
        raise RuntimeError("CTF_FLAG must use the SBOB{...} format.")

    with get_db() as connection:
        admin = connection.execute(
            "SELECT id, is_admin FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if admin is None:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
                ("admin", generate_password_hash(password)),
            )
            admin_id = cursor.lastrowid
        elif not admin["is_admin"]:
            raise RuntimeError("The reserved admin username is already in use.")
        else:
            admin_id = admin["id"]

        if flag:
            exists = connection.execute(
                "SELECT 1 FROM notes WHERE user_id = ? AND title = ?",
                (admin_id, "[SYSTEM] Boblink CTF verification"),
            ).fetchone()
            if exists is None:
                connection.execute(
                    "INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                    (admin_id, "[SYSTEM] Boblink CTF verification", flag),
                )


def csrf_token():
    token = session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.before_request
def prepare_request():
    g.csp_nonce = secrets.token_urlsafe(18)
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        with get_db() as connection:
            g.user = connection.execute(
                "SELECT id, username, is_admin, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if g.user is None:
            session.clear()

    expected_token = csrf_token()
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        submitted_token = request.form.get("csrf_token", "")
        if not secrets.compare_digest(expected_token, submitted_token):
            abort(400, description="Invalid request token.")


@app.after_request
def set_security_headers(response):
    nonce = getattr(g, "csp_nonce", "")
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"style-src 'nonce-{nonce}'; "
        "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; object-src 'none'"
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


def render_page(page_title, content, *, wide=False, **context):
    context["csrf_token"] = csrf_token()
    rendered_content = render_template_string(content, **context)
    return render_template_string(
        PAGE,
        title=page_title,
        content=rendered_content,
        csrf_token=context["csrf_token"],
        wide=wide,
    )


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("로그인이 필요합니다.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not g.user["is_admin"]:
            abort(404)
        return view(*args, **kwargs)

    return wrapped_view


def auth_rate_limited(scope, limit):
    key = (scope, request.remote_addr or "unknown")
    now = time.monotonic()
    with login_attempts_lock:
        if key not in login_attempts and len(login_attempts) >= MAX_RATE_LIMIT_BUCKETS:
            expired = [
                item_key
                for item_key, item_bucket in login_attempts.items()
                if not item_bucket or now - item_bucket[-1] > LOGIN_WINDOW_SECONDS
            ]
            for item_key in expired:
                login_attempts.pop(item_key, None)
            if len(login_attempts) >= MAX_RATE_LIMIT_BUCKETS:
                return True

        bucket = login_attempts.setdefault(key, deque())
        while bucket and now - bucket[0] > LOGIN_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False


def validate_note(title, content):
    title = title.strip()
    content = content.strip()
    if not title:
        return title, content, "제목을 입력해주세요."
    if len(title) > MAX_TITLE_LENGTH:
        return title, content, f"제목은 {MAX_TITLE_LENGTH}자 이하여야 합니다."
    if not content:
        return title, content, "내용을 입력해주세요."
    if len(content) > MAX_CONTENT_LENGTH:
        return title, content, f"내용은 {MAX_CONTENT_LENGTH}자 이하여야 합니다."
    return title, content, None


def note_storage_bytes(title, content):
    return len(title.encode("utf-8")) + len(content.encode("utf-8"))


def get_note_usage(connection, user_id, exclude_note_id=None):
    query = (
        "SELECT COUNT(*) AS note_count, "
        "COALESCE(SUM(length(CAST(title AS BLOB)) + "
        "length(CAST(content AS BLOB))), 0) AS storage_bytes "
        "FROM notes WHERE user_id = ?"
    )
    parameters = [user_id]
    if exclude_note_id is not None:
        query += " AND id != ?"
        parameters.append(exclude_note_id)
    return connection.execute(query, parameters).fetchone()


def format_storage(byte_count):
    if byte_count < 1024:
        return f"{byte_count} B"
    if byte_count >= 1024 * 1024:
        return f"{byte_count / (1024 * 1024):.1f} MiB"
    return f"{byte_count / 1024:.1f} KiB"


def get_owned_note(note_id):
    with get_db() as connection:
        note = connection.execute(
            "SELECT id, title, content, created_at, updated_at "
            "FROM notes WHERE id = ? AND user_id = ?",
            (note_id, g.user["id"]),
        ).fetchone()
    if note is None:
        abort(404)
    return note


@app.route("/")
@login_required
def index():
    with get_db() as connection:
        notes = connection.execute(
            "SELECT id, title, content, created_at, updated_at "
            "FROM notes WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
            (g.user["id"],),
        ).fetchall()
        usage = get_note_usage(connection, g.user["id"])

    content = """
    <div class="section-header">
        <div>
            <h2 class="memo-title">{{ g.user['username'] }}님의 메모</h2>
            <p>
                {{ usage['note_count'] }}/{{ max_notes }}개 ·
                {{ storage_used }}/{{ storage_limit }} 사용
            </p>
        </div>
        <a class="button" href="{{ url_for('create_note') }}">새 메모</a>
    </div>
    {% if notes %}
        <ul class="memo-list">
            {% for note in notes %}
                <li>
                    <a class="memo-item" href="{{ url_for('note_detail', note_id=note['id']) }}">
                        <p class="memo-title">{{ note['title'] }}</p>
                        <p class="memo-preview">{{ note['content']|truncate(120) }}</p>
                        <span class="memo-meta">최근 수정 {{ note['updated_at'] }}</span>
                    </a>
                </li>
            {% endfor %}
        </ul>
    {% else %}
        <div class="empty-state">아직 작성한 메모가 없습니다.</div>
    {% endif %}
    """
    return render_page(
        "내 메모",
        content,
        notes=notes,
        usage=usage,
        max_notes=MAX_NOTES_PER_USER,
        storage_used=format_storage(usage["storage_bytes"]),
        storage_limit=format_storage(MAX_USER_STORAGE_BYTES),
        wide=True,
    )


@app.route("/notes/new", methods=["GET", "POST"])
@login_required
def create_note():
    title = ""
    note_content = ""
    if request.method == "POST":
        title, note_content, error = validate_note(
            request.form.get("title", ""), request.form.get("content", "")
        )
        if error is None:
            with get_db() as connection:
                connection.execute("BEGIN IMMEDIATE")
                usage = get_note_usage(connection, g.user["id"])
                new_size = note_storage_bytes(title, note_content)
                if usage["note_count"] >= MAX_NOTES_PER_USER:
                    error = f"메모는 최대 {MAX_NOTES_PER_USER}개까지 저장할 수 있습니다."
                elif usage["storage_bytes"] + new_size > MAX_USER_STORAGE_BYTES:
                    error = (
                        "사용자당 메모 저장 용량 "
                        f"{format_storage(MAX_USER_STORAGE_BYTES)}를 초과했습니다."
                    )
                else:
                    cursor = connection.execute(
                        "INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                        (g.user["id"], title, note_content),
                    )
                    note_id = cursor.lastrowid
            if error is None:
                flash("메모를 저장했습니다.", "success")
                return redirect(url_for("note_detail", note_id=note_id))
        flash(error, "error")

    content = """
    <form method="post">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <p class="field">
            <label for="title">제목</label>
            <input id="title" name="title" maxlength="120" value="{{ title }}" required autofocus>
        </p>
        <p class="field">
            <label for="content">내용</label>
            <textarea id="content" name="content" maxlength="10000" required>{{ note_content }}</textarea>
        </p>
        <div class="memo-actions">
            <button type="submit">저장</button>
            <a class="button button-secondary" href="{{ url_for('index') }}">취소</a>
        </div>
    </form>
    """
    return render_page(
        "새 메모", content, title=title, note_content=note_content, wide=True
    )


@app.route("/notes/<int:note_id>")
@login_required
def note_detail(note_id):
    note = get_owned_note(note_id)
    content = """
    <div class="section-header">
        <div>
            <h2 class="memo-title">{{ note['title'] }}</h2>
            <p>최근 수정 {{ note['updated_at'] }}</p>
        </div>
        <div class="memo-actions">
            <a class="button button-secondary" href="{{ url_for('edit_note', note_id=note['id']) }}">수정</a>
            <form class="inline-form" method="post" action="{{ url_for('delete_note', note_id=note['id']) }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <button class="button-danger" type="submit">삭제</button>
            </form>
        </div>
    </div>
    <hr class="divider">
    <div class="note-content">{{ note['content'] }}</div>
    <hr class="divider">
    <a href="{{ url_for('index') }}">← 메모 목록</a>
    """
    return render_page("메모 상세", content, note=note, wide=True)


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    note = get_owned_note(note_id)
    title = note["title"]
    note_content = note["content"]
    if request.method == "POST":
        title, note_content, error = validate_note(
            request.form.get("title", ""), request.form.get("content", "")
        )
        if error is None:
            with get_db() as connection:
                connection.execute("BEGIN IMMEDIATE")
                usage = get_note_usage(
                    connection, g.user["id"], exclude_note_id=note_id
                )
                if (
                    usage["storage_bytes"]
                    + note_storage_bytes(title, note_content)
                    > MAX_USER_STORAGE_BYTES
                ):
                    error = (
                        "사용자당 메모 저장 용량 "
                        f"{format_storage(MAX_USER_STORAGE_BYTES)}를 초과했습니다."
                    )
                else:
                    result = connection.execute(
                        "UPDATE notes SET title = ?, content = ?, "
                        "updated_at = CURRENT_TIMESTAMP "
                        "WHERE id = ? AND user_id = ?",
                        (title, note_content, note_id, g.user["id"]),
                    )
                    if result.rowcount != 1:
                        abort(404)
            if error is None:
                flash("메모를 수정했습니다.", "success")
                return redirect(url_for("note_detail", note_id=note_id))
        flash(error, "error")

    content = """
    <form method="post">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <p class="field">
            <label for="title">제목</label>
            <input id="title" name="title" maxlength="120" value="{{ title }}" required autofocus>
        </p>
        <p class="field">
            <label for="content">내용</label>
            <textarea id="content" name="content" maxlength="10000" required>{{ note_content }}</textarea>
        </p>
        <div class="memo-actions">
            <button type="submit">변경사항 저장</button>
            <a class="button button-secondary" href="{{ url_for('note_detail', note_id=note['id']) }}">취소</a>
        </div>
    </form>
    """
    return render_page(
        "메모 수정",
        content,
        note=note,
        title=title,
        note_content=note_content,
        wide=True,
    )


@app.post("/notes/<int:note_id>/delete")
@login_required
def delete_note(note_id):
    with get_db() as connection:
        result = connection.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?",
            (note_id, g.user["id"]),
        )
    if result.rowcount != 1:
        abort(404)
    flash("메모를 삭제했습니다.", "success")
    return redirect(url_for("index"))


@app.route("/admin/users")
@admin_required
def admin_users():
    with get_db() as connection:
        users = connection.execute(
            "SELECT u.id, u.username, u.is_admin, u.created_at, COUNT(n.id) AS note_count "
            "FROM users AS u LEFT JOIN notes AS n ON n.user_id = u.id "
            "GROUP BY u.id, u.username, u.is_admin, u.created_at "
            "ORDER BY u.id ASC"
        ).fetchall()

    content = """
    <div class="section-header">
        <div>
            <h2 class="memo-title">전체 회원</h2>
            <p>관리자만 접근할 수 있는 회원 현황입니다.</p>
        </div>
        <span class="badge">{{ users|length }}명</span>
    </div>
    <div class="table-wrap">
        <table class="data-table">
            <thead><tr><th>ID</th><th>아이디</th><th>권한</th><th>메모</th><th>가입일</th></tr></thead>
            <tbody>
                {% for user in users %}
                    <tr>
                        <td>{{ user['id'] }}</td>
                        <td>{{ user['username'] }}</td>
                        <td>
                            <span class="badge{% if user['is_admin'] %} badge-admin{% endif %}">
                                {{ 'admin' if user['is_admin'] else 'member' }}
                            </span>
                        </td>
                        <td>{{ user['note_count'] }}</td>
                        <td>{{ user['created_at'] }}</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """
    return render_page("관리자", content, users=users, wide=True)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        if auth_rate_limited("signup", 5):
            abort(429)
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        error = None
        if not USERNAME_PATTERN.fullmatch(username):
            error = "아이디는 영문, 숫자, 점, 밑줄, 하이픈으로 3~32자여야 합니다."
        elif not 12 <= len(password) <= 128:
            error = "비밀번호는 12~128자여야 합니다."
        elif password != password_confirm:
            error = "비밀번호가 일치하지 않습니다."

        if error is None:
            try:
                with get_db() as connection:
                    connection.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
            except sqlite3.IntegrityError:
                error = "이미 사용 중인 아이디입니다."
            else:
                flash("회원가입이 완료되었습니다. 로그인해주세요.", "success")
                return redirect(url_for("login"))
        flash(error, "error")

    content = """
    <form method="post">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <p class="field">
            <label for="username">아이디</label>
            <input id="username" name="username" minlength="3" maxlength="32" pattern="[A-Za-z0-9_.-]+" autocomplete="username" required autofocus>
        </p>
        <p class="field">
            <label for="password">비밀번호</label>
            <input id="password" type="password" name="password" minlength="12" maxlength="128" autocomplete="new-password" required>
        </p>
        <p class="field">
            <label for="password-confirm">비밀번호 확인</label>
            <input id="password-confirm" type="password" name="password_confirm" minlength="12" maxlength="128" autocomplete="new-password" required>
        </p>
        <button class="button-block" type="submit">계정 만들기</button>
    </form>
    <p class="auth-switch">이미 계정이 있나요? <a href="{{ url_for('login') }}">로그인</a></p>
    """
    return render_page("회원가입", content)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        if auth_rate_limited("login", LOGIN_MAX_ATTEMPTS):
            flash("로그인 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.", "error")
            return render_page("로그인", LOGIN_FORM), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = None
        password_to_check = password if len(password) <= 128 else ""
        if len(username) <= 32:
            with get_db() as connection:
                user = connection.execute(
                    "SELECT id, username, password_hash FROM users WHERE username = ?",
                    (username,),
                ).fetchone()

        password_hash = user["password_hash"] if user else DUMMY_PASSWORD_HASH
        password_is_valid = check_password_hash(password_hash, password_to_check)
        if user is None or not password_is_valid:
            flash("아이디 또는 비밀번호가 올바르지 않습니다.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_urlsafe(32)
            session.permanent = True
            return redirect(url_for("index"))

    return render_page("로그인", LOGIN_FORM)


LOGIN_FORM = """
<form method="post">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <p class="field">
        <label for="username">아이디</label>
        <input id="username" name="username" maxlength="32" autocomplete="username" required autofocus>
    </p>
    <p class="field">
        <label for="password">비밀번호</label>
        <input id="password" type="password" name="password" maxlength="128" autocomplete="current-password" required>
    </p>
    <button class="button-block" type="submit">로그인</button>
</form>
<p class="auth-switch">처음 오셨나요? <a href="{{ url_for('signup') }}">계정 만들기</a></p>
"""


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("login"))


init_db()
bootstrap_admin()


if __name__ == "__main__":
    app.run()
