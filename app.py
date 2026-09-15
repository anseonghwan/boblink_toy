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
    <title>{{ title }}</title>
</head>
<body>
    <h1>{{ title }}</h1>

    {% with messages = get_flashed_messages() %}
        {% if messages %}
            <ul>
                {% for message in messages %}
                    <li>{{ message }}</li>
                {% endfor %}
            </ul>
        {% endif %}
    {% endwith %}

    {{ content|safe }}
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
            flash("로그인이 필요합니다.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
@login_required
def index():
    content = """
    <p><strong>{{ username }}</strong>님, 로그인되었습니다.</p>
    <p>메모 기능은 다음 단계에서 추가할 수 있습니다.</p>
    <p><a href="{{ url_for('logout') }}">로그아웃</a></p>
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
                flash("회원가입이 완료되었습니다. 로그인해주세요.")
                return redirect(url_for("login"))

        flash(error)

    content = """
    <form method="post">
        <p><label>아이디 <input name="username" required></label></p>
        <p><label>비밀번호 <input type="password" name="password" required></label></p>
        <p><label>비밀번호 확인 <input type="password" name="password_confirm" required></label></p>
        <button type="submit">회원가입</button>
    </form>
    <p><a href="{{ url_for('login') }}">로그인</a></p>
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
            flash("아이디 또는 비밀번호가 올바르지 않습니다.")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))

    content = """
    <form method="post">
        <p><label>아이디 <input name="username" required></label></p>
        <p><label>비밀번호 <input type="password" name="password" required></label></p>
        <button type="submit">로그인</button>
    </form>
    <p><a href="{{ url_for('signup') }}">회원가입</a></p>
    """
    return render_page("로그인", content)


@app.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("login"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
