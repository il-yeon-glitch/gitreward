# 웹 순위 페이지. cache/ 의 JSON 을 읽어 카드를 레벨 순으로 나열한다.
#
#   python web.py    ->  브라우저에서 http://127.0.0.1:5000
#
# HTML 은 이 파일 안에 문자열로 둔다. templates/ 폴더를 따로 만들지 않는다.

import os

from flask import Flask, render_template_string, url_for

from config import CARD_BG, CARD_ACCENT, CARD_TEXT, CARD_SUB, CARD_BAR_BG
from fetch import CACHE_DIR, load_cache, repo_from_cache_name
from stats import calc_stats, calc_level
from card import make_card

# Flask 는 static/ 폴더를 자동으로 웹에 열어준다.
# config.py 의 CARD_DIR 이 "static" 이라, 만든 카드가 그대로 주소를 갖게 된다.
app = Flask(__name__)


# config.py 의 색(숫자 3개)을 CSS 가 알아듣는 형태로 바꾼다.
# 색을 여기 직접 적지 않으려고 만든 함수다.
def css(color):
    return f"rgb({color[0]}, {color[1]}, {color[2]})"


COLORS = {
    "bg": css(CARD_BG),
    "accent": css(CARD_ACCENT),
    "text": css(CARD_TEXT),
    "sub": css(CARD_SUB),
    "barbg": css(CARD_BAR_BG),
}


# cache/ 를 전부 읽어 사람 목록을 만들고, 각자의 카드를 static/ 에 만든다.
# 새로고침할 때마다 카드를 다시 만든다. config.py 의 계수를 바꾸고
# 브라우저를 새로고침하면 바로 반영되니 밸런스를 맞출 때 편하다.
def load_people():
    people = []

    if not os.path.exists(CACHE_DIR):
        return people

    for name in sorted(os.listdir(CACHE_DIR)):
        if not name.endswith(".json"):
            continue

        # 파일 이름에서 저장소 이름을 되돌린다. 카드 파일명에 넣어야 한다.
        repo = repo_from_cache_name(name)

        for person in load_cache(os.path.join(CACHE_DIR, name)):
            stats = calc_stats(person)
            level = calc_level(stats)
            path = make_card(person, stats, level, repo)

            people.append({
                "login": person["login"],
                "repo": repo,
                "level": level,
                "stats": stats,
                "file": os.path.basename(path),
                # 브라우저는 한 번 받은 이미지를 주소가 같으면 다시 받지 않는다.
                # 카드를 새로 만들어도 옛날 그림이 그대로 보이는 이유다.
                # 파일이 바뀐 시각을 주소 뒤에 붙여 "다른 주소" 처럼 보이게 만든다.
                "v": int(os.path.getmtime(path)),
            })

    # 레벨이 높은 사람부터 보여준다.
    people.sort(key=lambda p: p["level"], reverse=True)

    return people


# {{ }} 안은 파이썬이 아니라 Flask 가 채워 넣는 자리다.
PAGE = """
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
  body {
    background: {{ bg }};
    color: {{ text }};
    font-family: "Malgun Gothic", sans-serif;
    margin: 0;
    padding: 32px;
  }
  a { color: {{ accent }}; text-decoration: none; }
  h1 { margin: 0 0 4px; font-size: 28px; }
  .sub { color: {{ sub }}; font-size: 14px; margin-bottom: 28px; }

  /* 여기 한 줄만 바꾸면 나열도 되고 두 장 나란히도 된다. */
  .grid {
    display: grid;
    gap: 20px;
    grid-template-columns: {{ columns }};
  }

  .item { background: {{ barbg }}; border-radius: 12px; padding: 12px; }
  .item img { width: 100%; display: block; border-radius: 8px; }
  .name { margin-top: 10px; font-size: 16px; }
  .meta { color: {{ sub }}; font-size: 12px; margin-top: 2px; }
  .empty { color: {{ sub }}; }
  footer { color: {{ sub }}; font-size: 12px; margin-top: 36px; }
</style>
</head>
<body>
  <h1>{{ title }}</h1>
  <div class="sub">{{ subtitle }}</div>

  {% if message %}
    <p class="empty">{{ message }}</p>
  {% endif %}

  <div class="grid">
    {% for p in people %}
      <div class="item">
        <img src="{{ url_for('static', filename=p.file, v=p.v) }}" alt="{{ p.login }}">
        <div class="name">{{ p.login }} &middot; Lv.{{ p.level }}</div>
        <div class="meta">{{ p.repo }}</div>
      </div>
    {% endfor %}
  </div>

  <footer>
    <a href="/">순위</a> &nbsp;|&nbsp;
    카드 두 장 나란히 보기: <code>/vs/아이디A/아이디B</code>
  </footer>
</body>
</html>
"""


@app.route("/")
def index():
    people = load_people()

    message = None
    if not people:
        message = "cache/ 에 JSON 이 없다. 먼저 python fetch.py owner/repo 를 실행한다."

    return render_template_string(
        PAGE,
        title="Git Reward",
        subtitle=f"참여자 {len(people)}명 · 레벨 순",
        people=people,
        # 화면 폭에 맞춰 몇 장이든 늘어놓는다.
        columns="repeat(auto-fill, minmax(260px, 1fr))",
        message=message,
        **COLORS,
    )


# 카드 두 장을 나란히 놓는 자리. 결투 규칙(승패)은 아직 없다.
# 레이아웃만 미리 잡아두는 것이라, 지금은 두 장을 골라 보여주기만 한다.
@app.route("/vs/<a>/<b>")
def vs(a, b):
    people = load_people()

    picked = []
    missing = []

    for want in (a, b):
        found = None
        for p in people:
            if p["login"].lower() == want.lower():
                found = p
                break

        if found is None:
            missing.append(want)
        else:
            picked.append(found)

    message = None
    if missing:
        message = f"찾을 수 없다: {', '.join(missing)}"

    return render_template_string(
        PAGE,
        title="카드 비교",
        subtitle="승패 규칙은 아직 없다. 나란히 놓기만 한다.",
        people=picked,
        # 두 칸으로 고정한다.
        columns="repeat(2, minmax(0, 1fr))",
        message=message,
        **COLORS,
    )


if __name__ == "__main__":
    # debug=True 로 켜면 코드를 고칠 때마다 서버가 알아서 다시 뜬다.
    app.run(debug=True)
