
from flask import Flask, render_template, jsonify, request, redirect, url_for, make_response
from datetime import datetime, timezone, timedelta
import time
import threading
import calendar as calendar_module
import re
import traceback
import json
import uuid
import os
import sqlite3
import secrets
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, g, flash
from pathlib import Path

import jpholiday

import requests
from bs4 import BeautifulSoup


app = Flask(__name__)
# 本番環境では環境変数 SECRET_KEY に十分長いランダム文字列を設定する。
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"

DATABASE_FILE = Path(__file__).with_name("meigen_users.sqlite3")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_FILE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_auth_db():
    with sqlite3.connect(DATABASE_FILE) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS personal_events (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            color TEXT NOT NULL DEFAULT 'blue',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        db.commit()


init_auth_db()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute(
        "SELECT id, username FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("予定を追加・編集するにはログインしてください。", "info")
            return redirect(url_for("login", next=request.full_path if request.query_string else request.path))
        return view(*args, **kwargs)
    return wrapped


def load_account_events(user_id):
    rows = get_db().execute(
        "SELECT id, date, title, detail, color FROM personal_events WHERE user_id = ? ORDER BY date, rowid",
        (user_id,),
    ).fetchall()
    return [dict(row, kind="personal") for row in rows]

JST = timezone(timedelta(hours=9))
WEEKDAYS = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日"]


# ==================================================
# 時間割
# ==================================================

CLASS_SCHEDULES = {
    "1組": {
        "月曜日": ["文学国語", "コミⅡ", "情報Ⅰ", "保健", "日本史/世界史", "数学ⅡBC", "論理国語"],
        "火曜日": ["数学ⅡBC", "数学ⅡBC", "日本史/世界史", "地理総合", "体育", "コミⅡ", "化学基礎"],
        "水曜日": ["古典探究", "情報Ⅰ", "数学ⅡBC", "論理表現Ⅱ", "総探", "総探"],
        "木曜日": ["地理総合", "数学ⅡBC", "論理国語", "論理表現Ⅱ", "コミⅡ", "体育", "日本史/世界史"],
        "金曜日": ["文学国語", "古典探究", "化学基礎", "日本史/世界史", "コミⅡ", "数学ⅡBC", "LHR"],
    },
    "2組": {
        "月曜日": ["論理国語", "コミⅡ", "文学国語", "情報Ⅰ", "日本史/世界史", "数学ⅡBC", "化学基礎"],
        "火曜日": ["数学ⅡBC", "数学ⅡBC", "日本史/世界史", "古典探究", "体育", "コミⅡ", "文学国語"],
        "水曜日": ["地理総合", "古典探究", "数学ⅡBC", "論理表現Ⅱ", "総探", "総探"],
        "木曜日": ["化学基礎", "数学ⅡBC", "保健", "論理表現Ⅱ", "コミⅡ", "体育", "日本史/世界史"],
        "金曜日": ["情報Ⅰ", "地理総合", "論理国語", "日本史/世界史", "コミⅡ", "数学ⅡBC", "LHR"],
    },
    "3組": {
        "月曜日": ["数学ⅡBC", "保健", "論理国語", "文学探究A", "コミⅡ", "化学基礎", "地理総合"],
        "火曜日": ["地理総合", "生物/物理", "コミⅡ", "数学ⅡBC", "情報Ⅰ", "体育", "化学基礎"],
        "水曜日": ["数学ⅡBC", "地理総合", "論理表現Ⅱ", "化学基礎", "総探", "総探"],
        "木曜日": ["化学基礎", "コミⅡ", "文学探究A", "体育", "数学ⅡBC", "生物/物理", "論理国語"],
        "金曜日": ["数学ⅡBC", "数学ⅡBC", "論理表現Ⅱ", "コミⅡ", "生物/物理", "情報Ⅰ", "LHR"],
    },
    "4組": {
        "月曜日": ["数学ⅡBC", "論理国語", "化学基礎", "地理総合", "コミⅡ", "文学探究A", "保健"],
        "火曜日": ["生物/物理", "情報Ⅰ", "コミⅡ", "数学ⅡBC", "文学探究A", "体育", "地理総合"],
        "水曜日": ["数学ⅡBC", "化学基礎", "論理表現Ⅱ", "情報Ⅰ", "総探", "総探"],
        "木曜日": ["論理国語", "コミⅡ", "地理総合", "体育", "数学ⅡBC", "化学基礎", "生物/物理"],
        "金曜日": ["数学ⅡBC", "数学ⅡBC", "論理表現Ⅱ", "コミⅡ", "化学基礎", "生物/物理", "LHR"],
    },
}

CLASS_NAMES = list(CLASS_SCHEDULES.keys())


# ==================================================
# 路線・天気の設定
# ==================================================

ROUTE_OPTIONS = {
    "tohoku_shinkansen": "東北新幹線",
    "utsunomiya": "JR宇都宮線",
    "ueno_tokyo": "上野東京ライン",
    "shonan_shinjuku": "湘南新宿ライン",
    "ryomo": "両毛線",
    "tobu_nikko": "東武日光線",
    "tobu_utsunomiya": "東武宇都宮線",
    "tobu_isesaki": "東武伊勢崎線",
    "tobu_sano": "東武佐野線",
}

WEATHER_OPTIONS = {
    "utsunomiya": "宇都宮市",
    "oyama": "小山市",
    "tochigi": "栃木市",
    "sano": "佐野市",
    "ashikaga": "足利市",
}


# ==================================================
# 運行情報の設定
# ==================================================

OPERATION_SOURCE_URL = "https://transit.yahoo.co.jp/diainfo/area/4"

OPERATION_SOURCE_URLS = {
    "tohoku_shinkansen": "https://transit.yahoo.co.jp/diainfo/1/0",
    "utsunomiya": "https://transit.yahoo.co.jp/diainfo/46/46",
    "ueno_tokyo": "https://transit.yahoo.co.jp/diainfo/627/0",
    "shonan_shinjuku": "https://transit.yahoo.co.jp/diainfo/25/0",
    "ryomo": "https://transit.yahoo.co.jp/diainfo/168/0",
    "tobu_nikko": "https://transit.yahoo.co.jp/diainfo/80/0",
    "tobu_utsunomiya": "https://transit.yahoo.co.jp/diainfo/169/0",
    "tobu_isesaki": "https://transit.yahoo.co.jp/diainfo/639/0",
    "tobu_sano": "https://transit.yahoo.co.jp/diainfo/172/0",
}

OPERATION_ROUTE_MATCHES = {
    "tohoku_shinkansen": ("東北新幹線",),
    "utsunomiya": (
        "宇都宮線[東京～宇都宮]",
        "宇都宮線[東京〜宇都宮]",
        "宇都宮線",
    ),
    "ueno_tokyo": ("上野東京ライン",),
    "shonan_shinjuku": ("湘南新宿ライン",),
    "ryomo": ("両毛線",),
    "tobu_nikko": (
        "東武日光線[南栗橋～東武日光]",
        "東武日光線[南栗橋〜東武日光]",
        "東武日光線",
    ),
    "tobu_utsunomiya": ("東武宇都宮線",),
    "tobu_isesaki": (
        "東武伊勢崎線[久喜～伊勢崎]",
        "東武伊勢崎線[久喜〜伊勢崎]",
        "東武伊勢崎線",
        "東武スカイツリーライン",
    ),
    "tobu_sano": ("東武佐野線",),
}

OPERATION_CACHE = {}
OPERATION_CACHE_SECONDS = 50

OPERATION_ALERT_CACHE = {
    "cached_at": 0,
    "data": [],
}
OPERATION_ALERT_CACHE_SECONDS = 50

OPERATION_LOCK = threading.Lock()


# ==================================================
# 学校行事
# ==================================================

SCHOOL_EVENTS = [
    {"date": "2026-10-27", "title": "心肺蘇生講習会", "detail": ""},
    {"date": "2026-10-28", "title": "⑤⑥SG大学講座", "detail": ""},
    {"date": "2026-10-28", "title": "第4回教科主任会", "detail": ""},
    {"date": "2026-10-29", "title": "40分授業", "detail": ""},
    {"date": "2026-10-30", "title": "進研模試(放課後)", "detail": ""},
    {"date": "2026-10-31", "title": "進研模試", "detail": ""},
    {"date": "2026-11-02", "title": "いじめ・教育相談アンケート", "detail": ""},
    {"date": "2026-11-04", "title": "⑤⑥講演会", "detail": ""},
    {"date": "2026-11-11", "title": "職員会議", "detail": ""},
    {"date": "2026-11-13", "title": "駅伝大会", "detail": ""},
    {"date": "2026-11-17", "title": "駅伝大会 予備日", "detail": ""},
    {"date": "2026-11-24", "title": "2学期期末試験 1日目", "detail": ""},
    {"date": "2026-11-25", "title": "2学期期末試験 2日目", "detail": ""},
    {"date": "2026-11-26", "title": "2学期期末試験 3日目", "detail": ""},
    {"date": "2026-11-27", "title": "2学期期末試験 4日目", "detail": ""},
    {"date": "2026-11-28", "title": "第6回教科主任会", "detail": ""},
    {"date": "2026-12-04", "title": "第2回授業評価アンケート", "detail": ""},
    {"date": "2026-12-12", "title": "土曜講座❹", "detail": ""},
    {"date": "2026-12-16", "title": "第7回教科主任会", "detail": ""},
    {"date": "2026-12-16", "title": "職員会議", "detail": ""},
]


# ==================================================
# 共通設定
# ==================================================

def selected_appearance():
    value = request.cookies.get("myHomeAppearance", "system")
    return value if value in ("light", "dark", "system") else "system"


@app.context_processor
def inject_appearance():
    return {"appearance": selected_appearance()}


@app.context_processor
def inject_auth_user():
    return {"logged_in_user": current_user()}


def selected_class():
    value = request.cookies.get("myHomeClass")
    return value if value in CLASS_SCHEDULES else None


def selected_route():
    value = request.cookies.get("myHomeRoute", "ryomo")
    return value if value in ROUTE_OPTIONS else "ryomo"


def selected_weather_place():
    value = request.cookies.get("myHomeWeather", "sano")
    return value if value in WEATHER_OPTIONS else "sano"


def filtered_events(now):
    """ホームの「今週の予定」用に学校行事・祝日・個人予定をまとめる。"""
    start = now.date()
    end = start + timedelta(days=7)
    result = []

    # 学校行事（青）
    for event in SCHOOL_EVENTS:
        try:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        except (ValueError, TypeError, KeyError):
            continue

        if start <= event_date <= end:
            result.append({
                **event,
                "date": event_date.isoformat(),
                "kind": "school",
                "event_color": "#077AE3",
                "text_color": "#0563B5",
            })

    # 日本の祝日（赤）
    day = start
    while day <= end:
        holiday_name = jpholiday.is_holiday_name(day)
        if holiday_name:
            result.append({
                "date": day.isoformat(),
                "title": holiday_name,
                "detail": "",
                "kind": "holiday",
                "event_color": "#E53935",
                "text_color": "#C62828",
            })
        day += timedelta(days=1)

    # ユーザーがカレンダーで追加した予定（設定した色）
    personal_events = load_personal_events()  # 既存データは全員共通のまま
    user = current_user()
    if user is not None:
        personal_events += load_account_events(user["id"])
    for event in personal_events:
        try:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        except (ValueError, TypeError, KeyError):
            continue

        if not start <= event_date <= end:
            continue

        color_key = event.get("color", "blue")
        if color_key not in PERSONAL_EVENT_COLORS:
            color_key = "blue"
        result.append({
            **event,
            "date": event_date.isoformat(),
            "kind": "personal",
            "color": color_key,
            "event_color": PERSONAL_EVENT_COLORS[color_key],
            "text_color": PERSONAL_EVENT_TEXT_COLORS[color_key],
        })

    # 日付順。同じ日は祝日→学校行事→個人予定の順で表示する。
    priority = {"holiday": 0, "school": 1, "personal": 2}
    return sorted(
        result,
        key=lambda item: (item["date"], priority.get(item.get("kind"), 9)),
    )


def _normalise_text(value):
    return " ".join(
        (value or "")
        .replace("\u3000", " ")
        .replace("\xa0", " ")
        .split()
    )


def _normalise_route_name(value):
    """路線名比較用。空白・全角半角の違いを整える。"""
    value = _normalise_text(value)
    value = value.replace("〜", "～")
    value = value.replace("－", "～")
    value = value.replace("−", "～")
    return value.strip()


def _operation_result(route_key, ok, status, detail, source_url):
    return {
        "ok": ok,
        "route": ROUTE_OPTIONS.get(route_key, "路線"),
        "status": status,
        "detail": detail,
        "updated_at": datetime.now(JST).strftime("%H:%M"),
        "source_url": source_url,
    }


# ==================================================
# ユーザー登録・ログイン
# ==================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user() is not None:
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not re.fullmatch(r"[A-Za-z0-9_ぁ-んァ-ヶ一-龠ー-]{3,24}", username):
            flash("ユーザー名は3〜24文字で入力してください（日本語・英数字・_ が使えます）。", "error")
        elif len(password) < 8 or len(password) > 128:
            flash("パスワードは8〜128文字で設定してください。", "error")
        else:
            try:
                db = get_db()
                cur = db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
                session.clear()
                session["user_id"] = cur.lastrowid
                flash("アカウントを作成しました。", "success")
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                flash("そのユーザー名はすでに使われています。", "error")
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user() is not None:
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT id, username, password_hash FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("ユーザー名またはパスワードが違います。", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash("ログインしました。", "success")
            destination = request.args.get("next", "")
            if not destination.startswith("/") or destination.startswith("//"):
                destination = url_for("home")
            return redirect(destination)
    return render_template("auth.html", mode="login")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("ログアウトしました。", "success")
    return redirect(url_for("home"))


# ==================================================
# ホーム
# ==================================================

@app.route("/")
def home():
    now = datetime.now(JST)

    weekday = (
        WEEKDAYS[now.weekday()]
        if now.weekday() < 5
        else ("土曜日" if now.weekday() == 5 else "日曜日")
    )

    class_name = selected_class()
    weather_place = selected_weather_place()

    today_lessons = (
        CLASS_SCHEDULES[class_name].get(weekday, [])
        if class_name
        else []
    )

    return render_template(
        "index.html",
        weekday=weekday,
        today_lessons=today_lessons,
        events=filtered_events(now),
        today=f"{now.year}年{now.month}月{now.day}日",
        class_name=class_name,
        class_names=CLASS_NAMES,
        weekday_short="月火水木金土日"[now.weekday()],
        weather_place=weather_place,
        weather_label=WEATHER_OPTIONS[weather_place],
        railway_label=ROUTE_OPTIONS[selected_route()],
    )


# ==================================================
# 週間時間割
# ==================================================

@app.route("/schedule", methods=["GET"])
def schedule():
    requested_class = request.args.get("class_name", "")

    class_name = (
        requested_class
        if requested_class in CLASS_SCHEDULES
        else selected_class()
    )

    return render_template(
        "schedule.html",
        schedule=CLASS_SCHEDULES.get(class_name, {}) if class_name else {},
        weekdays=WEEKDAYS,
        class_name=class_name,
        class_names=CLASS_NAMES,
    )


# ==================================================
# 設定
# ==================================================

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        class_name = request.form.get("class_name", "")
        my_route = request.form.get("my_route", "ryomo")
        weather_place = request.form.get("weather_place", "sano")
        appearance = request.form.get("appearance", "system")

        if class_name not in CLASS_SCHEDULES:
            class_name = ""
        if my_route not in ROUTE_OPTIONS:
            my_route = "ryomo"
        if weather_place not in WEATHER_OPTIONS:
            weather_place = "sano"
        if appearance not in ("light", "dark", "system"):
            appearance = "system"

        response = make_response(redirect(url_for("settings")))

        cookie_options = {
            "max_age": 60 * 60 * 24 * 365,
            "samesite": "Lax",
        }

        if class_name:
            response.set_cookie("myHomeClass", class_name, **cookie_options)
        else:
            response.delete_cookie("myHomeClass")

        response.set_cookie("myHomeRoute", my_route, **cookie_options)
        response.set_cookie("myHomeWeather", weather_place, **cookie_options)
        response.set_cookie("myHomeAppearance", appearance, **cookie_options)

        return response

    return render_template(
        "settings.html",
        class_name=selected_class(),
        class_names=CLASS_NAMES,
        my_route=selected_route(),
        route_options=ROUTE_OPTIONS,
        weather_place=selected_weather_place(),
        weather_options=WEATHER_OPTIONS,
    )


# ==================================================
# Yahoo!路線情報の解析
# ==================================================

def _get_page_soup(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    response = requests.get(url, headers=headers, timeout=(5, 12))
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"

    return BeautifulSoup(response.text, "html.parser")


def _clean_operation_container(soup):
    """
    運行情報本体を優先して残す。
    属性情報が None の HTML 要素があっても停止しない。
    """
    work = BeautifulSoup(str(soup), "html.parser")

    for tag in work.select(
        "script, style, noscript, template, iframe, svg, nav, footer"
    ):
        tag.decompose()

    for tag in list(work.find_all(True)):
        attrs = getattr(tag, "attrs", None)

        if not isinstance(attrs, dict):
            continue

        tag_id = attrs.get("id") or ""
        tag_classes = attrs.get("class") or []

        if isinstance(tag_classes, str):
            tag_classes = [tag_classes]

        marker = " ".join([
            str(tag_id),
            " ".join(str(value) for value in tag_classes),
        ]).lower()

        if any(word in marker for word in (
            "tweet", "twitter", "comment", "review",
            "userpost", "user-post", "social",
        )):
            tag.decompose()

    return work


def _extract_updated(text):
    patterns = [
        r"\d{1,2}月\d{1,2}日\s*\d{1,2}時\d{1,2}分\s*更新",
        r"\d{1,2}月\d{1,2}日\s*\d{1,2}時\d{1,2}分\s*現在",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return ""


# ==================================================
# 運行ステータスの判定
# ==================================================

def _find_status(text):
    """
    運行情報の文章から状態を判定する。
    「遅延情報はありません」などの否定表現を
    異常状態と誤判定しない。
    """
    text = _normalise_text(text)

    if not text:
        return "", -1

    # ------------------------------------------
    # 1. 平常運転を示す明確な文章を先に判定
    # ------------------------------------------
    normal_phrases = (
        "現在､事故･遅延に関する情報はありません",
        "現在、事故・遅延に関する情報はありません",
        "事故･遅延に関する情報はありません",
        "事故・遅延に関する情報はありません",
        "事故や遅延に関する情報はありません",
        "遅延に関する情報はありません",
        "遅れに関する情報はありません",
        "現在、運行情報はありません",
        "現在運行情報はありません",
        "平常運転",
    )

    for phrase in normal_phrases:
        index = text.find(phrase)
        if index >= 0:
            return "平常運転", index

    # ------------------------------------------
    # 2. 運転見合わせ・運転中止
    # ------------------------------------------
    suspension_options = (
        "運転見合わせ",
        "運転を見合わせ",
        "運転取りやめ",
        "運転を取りやめ",
        "運転中止",
        "運転を中止",
    )

    suspension_matches = [
        (text.find(phrase), phrase)
        for phrase in suspension_options
        if text.find(phrase) >= 0
    ]

    if suspension_matches:
        suspension_matches.sort(key=lambda item: item[0])
        index, phrase = suspension_matches[0]
        return phrase, index

    # ------------------------------------------
    # 3. 運転再開後も遅れ・運休が残る場合
    # ------------------------------------------
    has_restart = any(
        phrase in text
        for phrase in (
            "運転を再開",
            "運転再開",
            "運転を再開しました",
        )
    )

    has_remaining_disruption = any(
        phrase in text
        for phrase in (
            "遅れが出ています",
            "遅延が出ています",
            "一部列車に遅れ",
            "一部の列車に遅れ",
            "一部列車に運休",
            "一部の列車に運休",
            "一部運休",
            "遅れや運休",
            "遅延や運休",
        )
    )

    if has_restart and has_remaining_disruption:
        index = text.find("運転")
        return "遅延", index if index >= 0 else 0

    # ------------------------------------------
    # 4. 運休・遅延
    # ------------------------------------------
    disruption_options = (
        "一部運休",
        "列車遅延",
        "遅延",
        "遅れ",
        "運休",
    )

    disruption_matches = [
        (text.find(phrase), phrase)
        for phrase in disruption_options
        if text.find(phrase) >= 0
    ]

    if disruption_matches:
        disruption_matches.sort(key=lambda item: item[0])
        index, phrase = disruption_matches[0]
        return "遅延", index

    # ------------------------------------------
    # 5. その他の運行情報
    # ------------------------------------------
    if has_restart:
        index = text.find("運転")
        return "運転再開", index if index >= 0 else 0

    if "運転計画" in text:
        return "運転計画", text.find("運転計画")

    if "その他" in text:
        return "その他", text.find("その他")

    return "", -1


# ==================================================
# 運行情報の詳細文を抽出
# ==================================================

def _extract_detail(text, status, status_index):
    """運行情報の詳細文を抽出する。"""

    text = _normalise_text(text)

    if not text:
        return "詳細は情報元のページをご確認ください。"

    if status == "平常運転":
        return "事故・遅延に関する情報はありません。"

    # 更新日時を除去
    text = re.sub(
        r"\d{1,2}月\d{1,2}日\s*"
        r"\d{1,2}時\d{1,2}分\s*(?:更新|現在)",
        "",
        text,
    )

    # 掲載日時を除去
    text = re.sub(
        r"[（(]\s*\d{1,2}月\d{1,2}日.*?掲載\s*[）)]",
        "",
        text,
    )

    # 「運転状況」より後ろを対象にする
    marker = "運転状況"
    marker_index = text.find(marker)

    if marker_index >= 0:
        text = text[marker_index + len(marker):]

    # 迂回ルート検索や登録案内以降を除去
    stop_markers = (
        "迂回ルート検索",
        "路線を登録すると",
        "この路線に関するつぶやき",
        "みんなの運行情報",
        "運行情報を投稿",
        "Yahoo! JAPAN",
    )

    positions = [
        text.find(marker)
        for marker in stop_markers
        if text.find(marker) >= 0
    ]

    if positions:
        text = text[:min(positions)]

    text = _normalise_text(text)

    # 先頭に路線名が残っている場合は除去
    route_names = (
        "東武宇都宮線",
        "東武日光線",
        "東武伊勢崎線",
        "東武スカイツリーライン",
        "東武佐野線",
        "東北新幹線",
        "上野東京ライン",
        "湘南新宿ライン",
        "宇都宮線",
        "両毛線",
    )

    for route_name in route_names:
        if text.startswith(route_name):
            text = text[len(route_name):].strip()
            break

    text = _normalise_text(text)

    if not text:
        return "詳細は情報元のページをご確認ください。"

    return text[:4000]

# ==================================================
# Yahoo!運行情報ページの解析
# ==================================================

def _parse_operation_page(soup, route_key):
    """Yahoo!の路線個別ページから運行状況と詳細を取得する。"""
    route_label = ROUTE_OPTIONS.get(route_key, "路線")

    heading = soup.find("h1")

    if heading is None:
        raise ValueError("ページ内に路線名の見出しがありません")

    heading_text = _normalise_route_name(
        heading.get_text(" ", strip=True)
    )

    candidates = OPERATION_ROUTE_MATCHES.get(
        route_key,
        (route_label,),
    )

    candidate_names = {
        _normalise_route_name(name)
        for name in candidates
    }

    if heading_text not in candidate_names:
        raise ValueError(f"路線名が一致しません: {heading_text}")

    # HTML全体から見出し以降のテキストを取得する
    parts = []

    for item in heading.find_all_next(string=True):
        value = _normalise_text(str(item))

        if not value:
            continue

        if "に関するつぶやき" in value:
            break

        if "みんなの運行情報" in value:
            break

        parts.append(value)

    text = _normalise_text(" ".join(parts))
    print("[運行情報取得・確認] 路線:", route_label)
    print("[運行情報取得・確認] 取得文章:", text[:1500])

    text = re.sub(
        r"\d{1,2}月\d{1,2}日\s*"
        r"\d{1,2}時\d{1,2}分\s*(?:更新|現在)",
        "",
        text,
    )

    text = _normalise_text(text)

    status, status_index = _find_status(text)

    if not status:
        raise ValueError(
            f"{route_label}の運行状況を判定できません: {text[:250]}"
        )

    detail = _extract_detail(text, status, status_index)

    print(
        f"[運行情報解析] {route_label}: "
        f"status={status!r}, detail={detail[:200]!r}"
    )

    return status, detail

# ==================================================
# 選択中の路線の運行情報
# ==================================================

def fetch_operation_status(route_key):
    route_key = (
        route_key if route_key in ROUTE_OPTIONS else "ryomo"
    )

    route_label = ROUTE_OPTIONS[route_key]

    source_url = OPERATION_SOURCE_URLS.get(
        route_key,
        OPERATION_SOURCE_URL,
    )

    now = time.time()

    with OPERATION_LOCK:
        cached = OPERATION_CACHE.get(route_key)

        if (
            cached
            and now - cached["cached_at"] < OPERATION_CACHE_SECONDS
        ):
            return dict(cached["data"])

    try:
        soup = _get_page_soup(source_url)

        status, detail = _parse_operation_page(
            soup,
            route_key,
        )

        result = _operation_result(
            route_key,
            True,
            status,
            detail,
            source_url,
        )

    except Exception as exc:
        print(
            f"\n[運行情報取得エラー] {route_label}: {exc}"
        )
        traceback.print_exc()

        result = _operation_result(
            route_key,
            False,
            "取得できません",
            (
                "運行情報を取得・判定できませんでした。"
                "情報元のページで最新情報をご確認ください。"
            ),
            source_url,
        )

    with OPERATION_LOCK:
        OPERATION_CACHE[route_key] = {
            "cached_at": time.time(),
            "data": dict(result),
        }

    return dict(result)


# ==================================================
# 複数路線の運行異常情報
# ==================================================

def fetch_operation_alerts():
    now = time.time()

    with OPERATION_LOCK:
        cached_at = OPERATION_ALERT_CACHE["cached_at"]

        if now - cached_at < OPERATION_ALERT_CACHE_SECONDS:
            return [
                dict(item)
                for item in OPERATION_ALERT_CACHE["data"]
            ]

    alerts = []

    abnormal_statuses = (
        "運転見合わせ",
        "運転取りやめ",
        "運転中止",
        "一部運休",
        "運休",
        "列車遅延",
        "遅延",
        "運転計画",
        "運行情報あり",
        "その他",
        "運転再開",
    )

    for route_key, route_label in ROUTE_OPTIONS.items():
        operation = fetch_operation_status(route_key)

        status = _normalise_text(
            operation.get("status", "")
        )

        detail = _normalise_text(
            operation.get("detail", "")
        )

        source_url = operation.get(
            "source_url",
            OPERATION_SOURCE_URL,
        )

        if not operation.get("ok"):
            alerts.append({
                "route": route_label,
                "status": "取得できません",
                "detail": (
                    "運行状況を確認できません。"
                    "情報元のページで最新情報をご確認ください。"
                ),
                "updated_at": operation.get("updated_at"),
                "source_url": source_url,
                "icon": "warning.png",
            })
            continue

        if status == "平常運転":
            continue

        if not any(
            word in status for word in abnormal_statuses
        ):
            continue

        # 運転再開後も遅れ・運休が残る場合は遅延扱い
        if (
            "運転再開" in detail
            and any(
                word in detail
                for word in ("遅れ", "遅延", "運休")
            )
        ):
            status = "遅延"

        if any(word in status for word in (
            "運転見合わせ",
            "運転取りやめ",
            "運転中止",
            "一部運休",
            "運休",
        )):
            icon = "stop.png"

        elif "遅延" in status:
            icon = "delay.png"

        else:
            icon = "warning.png"

        alerts.append({
            "route": route_label,
            "status": status,
            "detail": detail or "詳細は情報元のページをご確認ください。",
            "updated_at": operation.get("updated_at"),
            "source_url": source_url,
            "icon": icon,
        })

    with OPERATION_LOCK:
        OPERATION_ALERT_CACHE["cached_at"] = time.time()
        OPERATION_ALERT_CACHE["data"] = [
            dict(item) for item in alerts
        ]

    return [
        dict(item)
        for item in alerts
    ]


# ==================================================
# 運行情報ページ
# ==================================================

@app.route("/operation")
def operation_page():
    route_key = selected_route()

    operation = fetch_operation_status(route_key)
    operation_alerts = fetch_operation_alerts()

    return render_template(
        "operation.html",
        operation=operation,
        operation_alerts=operation_alerts,
        railway_label=ROUTE_OPTIONS[route_key],
        weather_place=selected_weather_place(),
    )


# ==================================================
# ユーザー予定の保存
# ==================================================

PERSONAL_EVENTS_FILE = Path(__file__).with_name("personal_events.json")
PERSONAL_EVENTS_LOCK = threading.Lock()

PERSONAL_EVENT_COLORS = {
    "blue": "#077AE3",
    "red": "#E53935",
    "orange": "#F07800",
    "yellow": "#FDD835",
    "green": "#2E9D50",
    "purple": "#8E44AD",
    "pink": "#E84393",
}

# 予定名用の文字色。黄色も背景に埋もれないよう濃い色を使う。
PERSONAL_EVENT_TEXT_COLORS = {
    "blue": "#0563B5",
    "red": "#C62828",
    "orange": "#B94F00",
    "yellow": "#8A6D00",
    "green": "#20743A",
    "purple": "#71368A",
    "pink": "#B91F70",
}


def load_personal_events():
    """保存済みのユーザー予定を読み込む。"""
    with PERSONAL_EVENTS_LOCK:
        try:
            with PERSONAL_EVENTS_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                return []
            return [
                event for event in data
                if isinstance(event, dict)
                and event.get("id")
                and event.get("date")
                and event.get("title")
            ]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []


def save_personal_events(events):
    """ユーザー予定をJSONファイルへ保存する。"""
    with PERSONAL_EVENTS_LOCK:
        temporary_file = PERSONAL_EVENTS_FILE.with_suffix(".tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(events, file, ensure_ascii=False, indent=2)
        temporary_file.replace(PERSONAL_EVENTS_FILE)


# ==================================================
# カレンダー
# ==================================================

@app.route("/calendar", methods=["GET", "POST"])
def calendar_page():
    now = datetime.now(JST)

    if request.method == "POST":
        user = current_user()
        if user is None:
            flash("予定の追加・編集・削除にはログインが必要です。", "info")
            return redirect(url_for("login", next=url_for("calendar_page")))
        user_id = user["id"]
        action = request.form.get("action", "add")
        events = load_account_events(user_id)
        target_date = request.form.get("return_date", "")

        if action in ("edit", "delete"):
            # IDが一致するユーザー予定だけを操作する。祝日・学校行事は
            # SCHOOL_EVENTS / jpholiday 由来なので、このリストには存在しない。
            event_id = request.form.get("event_id", "")
            event = next((item for item in events if item.get("id") == event_id), None)

            if event is not None and action == "delete":
                get_db().execute("DELETE FROM personal_events WHERE id = ? AND user_id = ?", (event_id, user_id))
                get_db().commit()

            elif event is not None and action == "edit":
                event_date = request.form.get("event_date", "").strip()
                title = request.form.get("title", "").strip()
                detail = request.form.get("detail", "").strip()
                color = request.form.get("color", "blue").strip()
                if color not in PERSONAL_EVENT_COLORS:
                    color = "blue"

                try:
                    parsed_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                    valid_date = parsed_date.isoformat() == event_date
                except (ValueError, TypeError):
                    valid_date = False

                if valid_date and title:
                    event.update({
                        "date": event_date,
                        "title": title[:80],
                        "detail": detail[:300],
                        "color": color,
                        "kind": "personal",
                    })
                    get_db().execute(
                        "UPDATE personal_events SET date=?, title=?, detail=?, color=? WHERE id=? AND user_id=?",
                        (event_date, title[:80], detail[:300], color, event_id, user_id),
                    )
                    get_db().commit()
                    target_date = event_date

        elif action == "add":
            event_date = request.form.get("event_date", "").strip()
            title = request.form.get("title", "").strip()
            detail = request.form.get("detail", "").strip()
            color = request.form.get("color", "blue").strip()
            if color not in PERSONAL_EVENT_COLORS:
                color = "blue"

            try:
                parsed_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                valid_date = parsed_date.isoformat() == event_date
            except (ValueError, TypeError):
                valid_date = False

            if valid_date and title:
                get_db().execute(
                    "INSERT INTO personal_events (id, user_id, date, title, detail, color) VALUES (?, ?, ?, ?, ?, ?)",
                    (uuid.uuid4().hex, user_id, event_date, title[:80], detail[:300], color),
                )
                get_db().commit()
                target_date = event_date

        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
            return redirect(url_for(
                "calendar_page", year=target.year, month=target.month
            ))
        except (ValueError, TypeError):
            return redirect(url_for("calendar_page", year=now.year, month=now.month))

    try:
        year = int(request.args.get("year", now.year))
        month = int(request.args.get("month", now.month))
        if not 1 <= month <= 12 or not 1 <= year <= 9999:
            raise ValueError
    except (ValueError, TypeError):
        year, month = now.year, now.month

    month_calendar = calendar_module.Calendar(
        firstweekday=6
    ).monthdatescalendar(year, month)

    events_by_date = {}

    # 学校行事
    for event in SCHOOL_EVENTS:
        try:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        except (ValueError, TypeError, KeyError):
            continue
        events_by_date.setdefault(event_date.isoformat(), []).append({
            **event, "kind": "school"
        })

    # 既存の予定は全員共通。新規の予定はログインユーザーごとに表示する。
    personal_events = load_personal_events()
    user = current_user()
    if user is not None:
        personal_events += load_account_events(user["id"])
    for event in personal_events:
        try:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        except (ValueError, TypeError, KeyError):
            continue
        color_key = event.get("color", "blue")
        events_by_date.setdefault(event_date.isoformat(), []).append({
            **event,
            "kind": "personal",
            "color": color_key if color_key in PERSONAL_EVENT_COLORS else "blue",
        })

    # 日本の祝日（振替休日・国民の休日を含む）
    for week in month_calendar:
        for day in week:
            holiday_name = jpholiday.is_holiday_name(day)
            if holiday_name:
                events_by_date.setdefault(day.isoformat(), []).insert(0, {
                    "id": "holiday-" + day.isoformat(),
                    "date": day.isoformat(),
                    "title": holiday_name,
                    "detail": "",
                    "kind": "holiday",
                })

    holiday_dates = {
        day.isoformat()
        for week in month_calendar
        for day in week
        if jpholiday.is_holiday(day)
    }

    weeks = []
    for week in month_calendar:
        days = []
        for day in week:
            days.append({
                "date": day,
                "in_month": day.month == month,
                "is_holiday": day.isoformat() in holiday_dates,
                "events": events_by_date.get(day.isoformat(), []),
            })
        weeks.append(days)

    previous_year = year if month > 1 else year - 1
    previous_month = month - 1 if month > 1 else 12
    next_year = year if month < 12 else year + 1
    next_month = month + 1 if month < 12 else 1

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        weeks=weeks,
        today=now.date(),
        personal_event_colors=PERSONAL_EVENT_COLORS,
        personal_event_text_colors=PERSONAL_EVENT_TEXT_COLORS,
        previous_year=previous_year,
        previous_month=previous_month,
        next_year=next_year,
        next_month=next_month,
        weather_place=selected_weather_place(),
        railway_label=ROUTE_OPTIONS[selected_route()],
    )


# ==================================================
# その他
# ==================================================

@app.route("/more")
def more_page():
    return render_template(
        "more.html",
        weather_place=selected_weather_place(),
        railway_label=ROUTE_OPTIONS[selected_route()],
    )

# ==================================================
# その他：各ツールのページ
# ==================================================

@app.route("/roster")
def roster_page():
    return render_template(
        "tool_page.html",
        tool_name="名簿",
        description="名簿のページです。"
    )


@app.route("/recording")
def recording_page():
    return render_template(
        "tool_page.html",
        tool_name="録音",
        description="録音のページです。"
    )


@app.route("/stamp")
def stamp_page():
    return render_template(
        "tool_page.html",
        tool_name="スタンプ",
        description="スタンプのページです。"
    )


@app.route("/video")
def video_page():
    return render_template(
        "tool_page.html",
        tool_name="動画",
        description="動画のページです。"
    )


@app.route("/calculator")
def calculator_page():
    return render_template(
        "tool_page.html",
        tool_name="電卓",
        description="電卓のページです。"
    )

# ==================================================
# 運行情報API
# ==================================================

@app.route("/api/operation")
def api_operation():
    response = jsonify(
        fetch_operation_status(selected_route())
    )

    response.headers["Cache-Control"] = "no-store"

    return response


# ==================================================
# 複数路線の運行異常情報API
# ==================================================

@app.route("/api/operation-alerts")
def api_operation_alerts():
    response = jsonify({
        "alerts": fetch_operation_alerts(),
        "updated_at": datetime.now(JST).strftime("%H:%M"),
    })

    response.headers["Cache-Control"] = "no-store"

    return response


# ==================================================
# 時刻API
# ==================================================

@app.route("/api/time")
def api_time():
    now = datetime.now(JST)

    return jsonify({
        "time": now.strftime("%H:%M"),
        "date": f"{now.year}年{now.month}月{now.day}日",
        "weekday": "月火水木金土日"[now.weekday()],
    })


# ==================================================
# 起動
# ==================================================

if __name__ == "__main__":
    app.run(debug=True)