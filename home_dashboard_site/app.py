from flask import Flask, render_template, jsonify, request, redirect, url_for, make_response
from datetime import datetime, timezone, timedelta, date
import time
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
JST = timezone(timedelta(hours=9))
WEEKDAYS = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日"]

CLASS_TIMETABLES = {
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
CLASS_NAMES = list(CLASS_TIMETABLES.keys())
ROUTE_OPTIONS = {
    "tohoku_shinkansen": "東北新幹線", "utsunomiya": "JR宇都宮線",
    "ueno_tokyo": "上野東京ライン", "shonan_shinjuku": "湘南新宿ライン",
    "ryomo": "両毛線", "tobu_nikko": "東武日光線",
    "tobu_utsunomiya": "東武宇都宮線", "tobu_isesaki": "東武伊勢崎線",
    "tobu_sano": "東武佐野線",
}
WEATHER_OPTIONS = {"utsunomiya": "宇都宮市", "oyama": "小山市", "tochigi": "栃木市", "sano": "佐野市", "ashikaga": "足利市"}

# Yahoo!路線情報の関東エリア運行情報を参照します。
OPERATION_SOURCE_URL = "https://transit.yahoo.co.jp/diainfo/area/4"

OPERATION_SOURCE_URLS = {
    "tohoku_shinkansen": "https://transit.yahoo.co.jp/diainfo/1/0",
}
OPERATION_ROUTE_MATCHES = {
    "tohoku_shinkansen": ("東北新幹線",),
    "utsunomiya": ("宇都宮線[東京～宇都宮]", "宇都宮線[東京〜宇都宮]", "JR宇都宮線", "宇都宮線"),
    "ueno_tokyo": ("上野東京ライン",),
    "shonan_shinjuku": ("湘南新宿ライン",),
    "ryomo": ("両毛線",),
    "tobu_nikko": ("東武日光線",),
    "tobu_utsunomiya": ("東武宇都宮線",),
    "tobu_isesaki": ("東武伊勢崎線", "東武スカイツリーライン"),
    "tobu_sano": ("東武佐野線",),
}
OPERATION_CACHE = {}
OPERATION_CACHE_SECONDS = 50
SCHOOL_EVENTS = [
    {"date": "2026-10-27", "title": "心肺蘇生講習会", "detail": ""},
    {"date": "2026-10-28", "title": "⑤⑥SG大学講座", "detail": ""},
    {"date": "2026-10-28", "title": "第4回教科主任会", "detail": ""},
    {"date": "2026-10-29", "title": "40分授業", "detail": ""},
    {"date": "2026-10-30", "title": "進研模試(放課後)", "detail": ""},
    {"date": "2026-10-31", "title": "進研模試", "detail": ""},
    {"date": "2026-11-2", "title": "いじめ・教育相談アンケート", "detail": ""},
    {"date": "2026-11-4", "title": "⑤⑥講演会", "detail": ""},
    {"date": "2026-11-11", "title": "職員会議", "detail": ""},
    {"date": "2026-11-13", "title": "駅伝大会", "detail": ""},
    {"date": "2026-11-17", "title": "駅伝大会 予備日", "detail": ""},
    {"date": "2026-11-28", "title": "第6回教科主任会", "detail": ""},
    {"date": "2026-11-24", "title": "2学期期末試験 1日目", "detail": ""},
    {"date": "2026-11-25", "title": "2学期期末試験 2日目", "detail": ""},
    {"date": "2026-11-26", "title": "2学期期末試験 3日目", "detail": ""},
    {"date": "2026-11-27", "title": "2学期期末試験 4日目", "detail": ""},
    {"date": "2026-12-4", "title": "第2回授業評価アンケート", "detail": ""},
    {"date": "2026-12-12", "title": "土曜講座❹", "detail": ""},
    {"date": "2026-12-16", "title": "第7回教科主任会", "detail": ""},
    {"date": "2026-12-16", "title": "職員会議", "detail": ""},
]

def selected_appearance():
    value = request.cookies.get("myHomeAppearance", "system")
    return value if value in ("light", "dark", "system") else "system"

@app.context_processor
def inject_appearance():
    return {"appearance": selected_appearance()}

def selected_class():
    value = request.cookies.get("myHomeClass")
    return value if value in CLASS_TIMETABLES else None

def selected_route():
    value = request.cookies.get("myHomeRoute", "ryomo")
    return value if value in ROUTE_OPTIONS else "ryomo"

def selected_weather_place():
    value = request.cookies.get("myHomeWeather", "sano")
    return value if value in WEATHER_OPTIONS else "sano"

def filtered_events(now):
    start = now.date()
    end = start + timedelta(days=7)
    result = []
    for event in SCHOOL_EVENTS:
        try:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        except (ValueError, TypeError, KeyError):
            continue
        if start <= event_date <= end:
            item = dict(event)
            item["date"] = event_date.strftime("%Y-%m-%d")
            result.append(item)
    return sorted(result, key=lambda item: item["date"])

@app.route("/")
def home():
    now = datetime.now(JST)
    weekday = WEEKDAYS[now.weekday()] if now.weekday() < 5 else ("土曜日" if now.weekday() == 5 else "日曜日")
    class_name = selected_class()
    weather_place = selected_weather_place()
    today_lessons = CLASS_TIMETABLES[class_name].get(weekday, []) if class_name else []
    return render_template(
        "index.html", weekday=weekday, today_lessons=today_lessons,
        events=filtered_events(now), today=f"{now.year}年{now.month}月{now.day}日",
        class_name=class_name, class_names=CLASS_NAMES,
        weekday_short="月火水木金土日"[now.weekday()],
        weather_place=weather_place, weather_label=WEATHER_OPTIONS[weather_place],
        railway_label=ROUTE_OPTIONS[selected_route()],
    )

@app.route("/timetable", methods=["GET"])
def timetable():
    # 週間時間割ページでのクラス選択はURLのクエリだけで管理し、設定のクラス選択Cookieは変更しない。
    requested_class = request.args.get("class_name", "")
    if requested_class in CLASS_TIMETABLES:
        class_name = requested_class
    else:
        # クラス指定がない初回表示では、設定で選択中のクラスを表示する。
        class_name = selected_class()
    return render_template("timetable.html", timetable=CLASS_TIMETABLES.get(class_name, {}) if class_name else {},
                           weekdays=WEEKDAYS, class_name=class_name, class_names=CLASS_NAMES)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        class_name = request.form.get("class_name", "")
        my_route = request.form.get("my_route", "ryomo")
        weather_place = request.form.get("weather_place", "sano")
        appearance = request.form.get("appearance", "system")
        if class_name not in CLASS_TIMETABLES:
            class_name = ""
        if my_route not in ROUTE_OPTIONS:
            my_route = "ryomo"
        if weather_place not in WEATHER_OPTIONS:
            weather_place = "sano"
        if appearance not in ("light", "dark", "system"):
            appearance = "system"
        response = make_response(redirect(url_for("settings")))
        if class_name:
            response.set_cookie("myHomeClass", class_name, max_age=60*60*24*365, samesite="Lax")
        else:
            response.delete_cookie("myHomeClass")
        response.set_cookie("myHomeRoute", my_route, max_age=60*60*24*365, samesite="Lax")
        response.set_cookie("myHomeWeather", weather_place, max_age=60*60*24*365, samesite="Lax")
        response.set_cookie("myHomeAppearance", appearance, max_age=60*60*24*365, samesite="Lax")
        return response
    return render_template("settings.html", class_name=selected_class(), class_names=CLASS_NAMES,
                           my_route=selected_route(), route_options=ROUTE_OPTIONS,
                           weather_place=selected_weather_place(), weather_options=WEATHER_OPTIONS)

def _normalise_text(value):
    return " ".join((value or "").replace("\u3000", " ").split())


def fetch_operation_status(route_key):
    """選択路線の運行情報を取得する。失敗時は平常運転と誤表示しない。"""
    route_label = ROUTE_OPTIONS.get(route_key, ROUTE_OPTIONS["ryomo"])
    source_url = OPERATION_SOURCE_URLS.get(
        route_key, OPERATION_SOURCE_URL
    )

    now = time.time()
    cached = OPERATION_CACHE.get(route_key)

    if cached and now - cached["cached_at"] < OPERATION_CACHE_SECONDS:
        return dict(cached["data"])

    try:
        response = requests.get(
            source_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
                )
            },
            timeout=10,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        candidates = OPERATION_ROUTE_MATCHES.get(
            route_key, (route_label,)
        )

        matched_row = None

        # まず、従来のエリアページから路線の行を探す。
        for row in soup.find_all("tr"):
            links = [
                _normalise_text(a.get_text(" ", strip=True))
                for a in row.find_all("a")
            ]
            row_text = _normalise_text(row.get_text(" ", strip=True))

            if not row_text:
                continue

            for candidate in candidates:
                if (
                    any(candidate in link for link in links)
                    or candidate in row_text
                ):
                    if route_key == "utsunomiya":
                        if (
                            "宇都宮線" in row_text
                            and (
                                "宇都宮～黒磯" in row_text
                                or "宇都宮〜黒磯" in row_text
                            )
                        ):
                            continue

                    matched_row = row
                    break

            if matched_row is not None:
                break

        status = ""
        detail = ""

        if matched_row is not None:
            cells = [
                _normalise_text(
                    cell.get_text(" ", strip=True)
                )
                for cell in matched_row.find_all(["th", "td"])
            ]
            row_text = _normalise_text(
                matched_row.get_text(" ", strip=True)
            )

            status_options = (
                "平常運転",
                "列車遅延",
                "遅延",
                "運転見合わせ",
                "一部運休",
                "運休",
                "運転計画",
                "その他",
            )

            for cell in cells:
                found = next(
                    (s for s in status_options if s in cell),
                    None,
                )
                if found:
                    status = found
                    break

            if status:
                status_index = next(
                    (
                        i for i, cell in enumerate(cells)
                        if status in cell
                    ),
                    -1,
                )
                if status_index >= 0:
                    detail = " ".join(
                        cells[status_index + 1:]
                    ).strip()

            if not status:
                if (
                    "事故・遅延情報はありません" in row_text
                    or "事故･遅延情報はありません" in row_text
                ):
                    status = "平常運転"
                    detail = "事故・遅延情報はありません。"
                else:
                    status = "運行情報あり"
                    detail = row_text

            if not detail:
                detail = (
                    "事故・遅延情報はありません。"
                    if status == "平常運転"
                    else row_text
                )

        elif route_key == "tohoku_shinkansen":
            # 東北新幹線の専用ページは、エリア一覧の
            # 表形式とは異なる場合があるため、ページ全体を確認する。
            page_text = _normalise_text(
                soup.get_text(" ", strip=True)
            )

            if "平常運転" in page_text:
                status = "平常運転"
                detail = "事故・遅延情報はありません。"
            else:
                status_options = (
                    "運転見合わせ",
                    "列車遅延",
                    "一部運休",
                    "運転計画",
                    "運休",
                    "遅延",
                    "その他",
                )

                for option in status_options:
                    if option in page_text:
                        status = option
                        detail = (
                            "詳細は情報元のページをご確認ください。"
                        )
                        break

            if not status:
                raise ValueError(
                    "東北新幹線の運行状況を判別できません"
                )

        else:
            raise ValueError(
                "選択した路線が運行情報ページに見つかりません"
            )

        result = {
            "ok": True,
            "route": route_label,
            "status": status,
            "detail": detail[:280],
            "updated_at": datetime.now(JST).strftime("%H:%M:%S"),
            "source_url": source_url,
        }

    except Exception as exc:
        print(
            f"[運行情報取得エラー] {route_label}: {exc}"
        )

        result = {
            "ok": False,
            "route": route_label,
            "status": "取得できません",
            "detail": (
                "運行情報を取得できません。"
                "時間をおいて再読み込みしてください。"
            ),
            "updated_at": datetime.now(JST).strftime("%H:%M:%S"),
            "source_url": source_url,
        }

    OPERATION_CACHE[route_key] = {
        "cached_at": now,
        "data": result,
    }

    return dict(result)


@app.route("/api/operation")
def api_operation():
    return jsonify(fetch_operation_status(selected_route()))

@app.route("/api/time")
def api_time():
    now = datetime.now(JST)
    return jsonify({"time": now.strftime("%H:%M:%S"), "date": f"{now.year}年{now.month}月{now.day}日",
                    "weekday": "月火水木金土日"[now.weekday()]})

if __name__ == "__main__":
    app.run(debug=True)
