# 웹 순위 페이지. cache/ 의 JSON 을 읽어 카드를 레벨 순으로 나열한다.
#
#   python web.py    ->  브라우저에서 http://127.0.0.1:5000
#
# HTML 은 이 파일 안에 문자열로 둔다. templates/ 폴더를 따로 만들지 않는다.

import os

from flask import Flask, render_template_string, url_for

from config import CARD_BG, CARD_ACCENT, CARD_TEXT, CARD_SUB, CARD_BAR_BG
from fetch import CACHE_DIR, load_cache, repo_from_cache_name
from stats import calc_stats, calc_level, calc_grade
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
def load_people(only_repo=None):
    people = []

    if not os.path.exists(CACHE_DIR):
        return people

    for name in sorted(os.listdir(CACHE_DIR)):
        if not name.endswith(".json"):
            continue

        # 파일 이름에서 저장소 이름을 되돌린다. 카드 파일명에 넣어야 한다.
        repo = repo_from_cache_name(name)

        # only_repo 가 있으면 그 저장소 하나만 남긴다. /project/<owner>/<repo> 가 쓴다.
        if only_repo is not None and repo != only_repo:
            continue

        for person in load_cache(os.path.join(CACHE_DIR, name)):
            stats = calc_stats(person)
            level = calc_level(stats)
            path = make_card(person, stats, level, repo)

            people.append({
                "login": person["login"],
                "repo": repo,
                "level": level,
                "grade": calc_grade(level),
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

  nav { margin-bottom: 28px; }
  nav a { font-size: 20px; font-weight: bold; margin-right: 24px; }

  /* 홈 화면만 이 클래스를 써서 정중앙에 놓는다. */
  .hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    min-height: 70vh;
  }

  form { margin-bottom: 28px; }
  input {
    background: {{ barbg }};
    color: {{ text }};
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    width: 240px;
  }
  button {
    background: {{ accent }};
    color: {{ bg }};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 14px;
    margin-left: 8px;
    cursor: pointer;
  }

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

  /* S 등급 카드에만 붙는 반짝이는 효과. 마우스를 올리면 카드가 기울고 빛이 지나간다.
     디스코드로 보내는 PNG 는 정적 이미지라 이 효과를 못 넣는다 — 웹 페이지 전용이다. */
  .holo-container { position: relative; transition: transform 0.1s; }
  .holo-overlay {
    position: absolute;
    inset: 12px 12px auto 12px;
    border-radius: 8px;
    aspect-ratio: 2 / 3;
    background: linear-gradient(105deg,
      transparent 40%,
      rgba(255, 219, 112, 0.8) 45%,
      rgba(132, 50, 255, 0.6) 50%,
      transparent 54%);
    background-size: 150% 150%;
    background-position: 100%;
    filter: brightness(1.1) opacity(0);
    mix-blend-mode: color-dodge;
    transition: filter 0.1s, background-position 0.1s;
    pointer-events: none;
  }
</style>
</head>
<body>
  <nav>
    <a href="/">홈</a>
    <a href="/all">전체 순위</a>
  </nav>

  {% if home %}
    <div class="hero">
      <h1>{{ title }}</h1>
      <div class="sub">{{ subtitle }}</div>

      <form onsubmit="location.href = '/project/' + document.getElementById('repo-input').value.trim(); return false;">
        <input id="repo-input" type="text" placeholder="owner/repo">
        <button type="submit">프로젝트 보기</button>
      </form>
    </div>
  {% else %}
    <h1>{{ title }}</h1>
    <div class="sub">{{ subtitle }}</div>

    <form onsubmit="location.href = '/project/' + document.getElementById('repo-input').value.trim(); return false;">
      <input id="repo-input" type="text" placeholder="owner/repo">
      <button type="submit">프로젝트 보기</button>
    </form>

    {% if message %}
      <p class="empty">{{ message }}</p>
    {% endif %}

    <div class="grid">
      {% for p in people %}
        <div class="item{% if p.grade == 'S' %} holo-container{% endif %}">
          {% if p.grade == 'S' %}<div class="holo-overlay"></div>{% endif %}
          <img src="{{ url_for('static', filename=p.file, v=p.v) }}" alt="{{ p.login }}">
          <div class="name">{{ p.login }} &middot; Lv.{{ p.level }}</div>
          <div class="meta">{{ p.repo }}</div>
        </div>
      {% endfor %}
    </div>
  {% endif %}

  <script>
    // S 등급 카드(.holo-container)에만 붙는다. 마우스 위치에 따라 카드를
    // 살짝 기울이고, 대각선 빛 띠(.holo-overlay)를 그 위로 지나가게 한다.
    document.querySelectorAll('.holo-container').forEach(function (container) {
      var overlay = container.querySelector('.holo-overlay')

      container.addEventListener('mousemove', function (e) {
        var rect = container.getBoundingClientRect()
        // 카드 크기가 화면마다 다르니, 픽셀이 아니라 0~1 비율로 계산해야
        // 큰 카드에서도 작은 카드와 똑같은 기울기가 나온다.
        var px = (e.clientX - rect.left) / rect.width
        var py = (e.clientY - rect.top) / rect.height

        var rotateY = (0.5 - px) * 40
        var rotateX = (py - 0.5) * 40

        overlay.style.backgroundPosition = ((px + py) * 50) + '%'
        overlay.style.filter = 'brightness(1.2) opacity(' + px.toFixed(2) + ')'
        container.style.transform =
          'perspective(800px) rotateX(' + rotateX.toFixed(1) + 'deg) rotateY(' + rotateY.toFixed(1) + 'deg)'
      })

      container.addEventListener('mouseout', function () {
        overlay.style.filter = 'brightness(1.1) opacity(0)'
        container.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg)'
      })
    })
  </script>
</body>
</html>
"""


# 홈 화면. 카드를 하나도 안 불러온다 — cache/ 가 커지면 전부 그리는 데
# 오래 걸리는데, 여기서는 그럴 필요가 없다. 저장소 주소를 넣는 창만 보여준다.
@app.route("/")
def index():
    return render_template_string(
        PAGE,
        title="Git Reward",
        subtitle="저장소 주소(owner/repo)를 넣으면 카드를 볼 수 있다",
        people=[],
        columns="repeat(auto-fill, minmax(260px, 1fr))",
        message=None,
        home=True,
        **COLORS,
    )


# 전체 순위. 예전 "/" 가 하던 일을 그대로 옮겼다.
@app.route("/all")
def all_projects():
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


# 저장소 하나만 골라 보여주는 자리. bot.py 의 /등록, /목록 이 안내하는 링크가 여기로 온다.
@app.route("/project/<owner>/<repo>")
def project(owner, repo):
    combined = f"{owner}/{repo}"
    people = load_people(only_repo=combined)

    message = None
    if not people:
        message = f"{combined} 를 찾을 수 없다. 먼저 디스코드에서 /등록 으로 추가한다."

    return render_template_string(
        PAGE,
        title=combined,
        subtitle=f"참여자 {len(people)}명 · 레벨 순",
        people=people,
        columns="repeat(auto-fill, minmax(260px, 1fr))",
        message=message,
        **COLORS,
    )


if __name__ == "__main__":
    # debug=True 로 켜면 코드를 고칠 때마다 서버가 알아서 다시 뜬다.
    app.run(debug=True)
