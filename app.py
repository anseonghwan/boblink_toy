import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "memo.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "development-secret-key-change-before-deployment"
)

PAGE = """
<!doctype html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} · Boblink Memo</title>
    <style>
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
        input:focus-visible {
            outline: 2px solid var(--accent-hover);
            outline-offset: 2px;
        }

        .page-shell {
            width: min(100% - 32px, 440px);
            margin: 0 auto;
            padding: 64px 0;
        }

        .brand {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 28px;
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

        @media (max-width: 520px) {
            .page-shell { width: min(100% - 24px, 440px); padding: 32px 0; }
            .card-header, .card-body { padding-right: 20px; padding-left: 20px; }
            .flash-list { margin-right: 20px; margin-left: 20px; }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { transition: none !important; }
        }
    </style>
</head>
<body>
    <main class="page-shell">
        <a class="brand" href="{{ url_for('index') }}" aria-label="Boblink Memo 홈">
            <span class="brand-mark" aria-hidden="true">B</span>
            <span>Boblink Memo</span>
        </a>

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


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )


def render_page(title, content, **context):
    rendered_content = render_template_string(content, **context)
    return render_template_string(PAGE, title=title, content=rendered_content)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("로그인이 필요합니다.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
@login_required
def index():
    content = """
    <div class="welcome">
        <div class="avatar" aria-hidden="true">{{ username[0]|upper }}</div>
        <div>
            <p class="welcome-title">{{ username }}님, 반갑습니다.</p>
            <p class="welcome-copy">안전하게 로그인되어 있습니다.</p>
        </div>
    </div>
    <hr class="divider">
    <p class="welcome-copy">메모 기능은 다음 단계에서 이곳에 추가됩니다.</p>
    <p><a class="button button-secondary button-block" href="{{ url_for('logout') }}">로그아웃</a></p>
    """
    return render_page("메모 서비스", content, username=session["username"])


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        error = None
        if not username:
            error = "아이디를 입력해주세요."
        elif not password:
            error = "비밀번호를 입력해주세요."
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
        <p class="field">
            <label for="username">아이디</label>
            <input id="username" name="username" autocomplete="username" required autofocus>
        </p>
        <p class="field">
            <label for="password">비밀번호</label>
            <input id="password" type="password" name="password" autocomplete="new-password" required>
        </p>
        <p class="field">
            <label for="password-confirm">비밀번호 확인</label>
            <input id="password-confirm" type="password" name="password_confirm" autocomplete="new-password" required>
        </p>
        <button class="button-block" type="submit">계정 만들기</button>
    </form>
    <p class="auth-switch">이미 계정이 있나요? <a href="{{ url_for('login') }}">로그인</a></p>
    """
    return render_page("회원가입", content)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as connection:
            user = connection.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("아이디 또는 비밀번호가 올바르지 않습니다.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))

    content = """
    <form method="post">
        <p class="field">
            <label for="username">아이디</label>
            <input id="username" name="username" autocomplete="username" required autofocus>
        </p>
        <p class="field">
            <label for="password">비밀번호</label>
            <input id="password" type="password" name="password" autocomplete="current-password" required>
        </p>
        <button class="button-block" type="submit">로그인</button>
    </form>
    <p class="auth-switch">처음 오셨나요? <a href="{{ url_for('signup') }}">계정 만들기</a></p>
    """
    return render_page("로그인", content)


@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("login"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
