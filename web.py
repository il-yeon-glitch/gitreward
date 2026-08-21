# 웹 순위 페이지. cache/ 의 JSON 을 읽어 카드를 레벨 순으로 나열한다.
#
#   python web.py    ->  브라우저에서 http://127.0.0.1:5000
#
# HTML 은 이 파일 안에 문자열로 둔다. templates/ 폴더를 따로 만들지 않는다.

import os
from urllib.parse import urlencode

import ngrok
import requests
from flask import Flask, render_template_string, url_for, request, redirect

import db
from config import (
    CARD_BG, CARD_ACCENT, CARD_TEXT, CARD_SUB, CARD_BAR_BG,
    WEB_BASE_URL, NGROK_DOMAIN, WEB_PORT, GAME_BASE_URL,
    GITHUB_OAUTH_AUTHORIZE_URL, GITHUB_OAUTH_TOKEN_URL, GITHUB_API_USER_URL,
)
from fetch import CACHE_DIR, load_cache, repo_from_cache_name
from stats import calc_legacy_stats, calc_level, calc_grade
from card import make_card, card_stats

# Flask 는 static/ 폴더를 자동으로 웹에 열어준다.
# config.py 의 CARD_DIR 이 "static" 이라, 만든 카드가 그대로 주소를 갖게 된다.
app = Flask(__name__)

# 로그인(계정 연결) 테이블이 없으면 여기서 만든다. bot.py 도 시작할 때 따로 부른다.
db.init_db()


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
            # 레벨은 기여 기록에서, 카드에 그릴 HP/ATK/DEF 는 레벨 + 배분 포인트에서 나온다.
            level = calc_level(calc_legacy_stats(person))
            stats = card_stats(person, level, repo)
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

  /* 카드를 <a> 로 감싸서 클릭하면 /game/<login> 으로 가게 한다.
     <a> 는 기본이 inline 이라 block 을 안 주면 div 로 있을 때와 레이아웃이 달라진다. */
  .item { display: block; background: {{ barbg }}; border-radius: 12px; padding: 12px; }
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
        <a class="item{% if p.grade in ['S', 'A'] %} holo-container{% endif %}" href="/game/{{ p.login }}">
          {% if p.grade in ['S', 'A'] %}<div class="holo-overlay"></div>{% endif %}
          <img src="{{ url_for('static', filename=p.file, v=p.v) }}" alt="{{ p.login }}">
          <div class="name">{{ p.login }} &middot; Lv.{{ p.level }}</div>
          <div class="meta">{{ p.repo }}</div>
        </a>
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


# 카드를 클릭했을 때 오는 비번 입력 화면. PAGE 와 따로 둔 건 nav/grid 가 필요 없는
# 훨씬 단순한 화면이라서다.
GAME_GATE_PAGE = """
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ login }} 인증</title>
<style>
  body {
    background: {{ bg }};
    color: {{ text }};
    font-family: "Malgun Gothic", sans-serif;
    margin: 0;
    padding: 32px;
  }
  .hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    min-height: 70vh;
  }
  .sub { color: {{ sub }}; font-size: 14px; margin-bottom: 20px; }
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
  .error { color: #e06060; margin-top: 12px; }
</style>
</head>
<body>
  <div class="hero">
    <h1>{{ login }}</h1>
    <div class="sub">이 카드로 게임에 들어가려면, 디스코드 `/비밀번호확인` 으로 받은 비번을 입력한다</div>

    <form method="post">
      <input type="password" name="password" placeholder="비번" autofocus>
      <button type="submit">입장</button>
    </form>

    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}
  </div>
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


# 카드 두 장을 나란히 놓던 /vs/<a>/<b> 는 2026-08-21 기획 결정으로 없앴다.
# 카드 결투가 기획에서 빠지면서 이 자리를 쓸 일이 없어졌다.


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


# 카드를 클릭했을 때 오는 자리. 비번을 맞혀야 게임으로 넘어간다.
# 비번은 discord_id 에 묶여 있는데 여기서는 github_login 만 아니까,
# db.verify_password_by_login() 으로 login -> discord_id 를 되짚어 비번을 확인한다.
@app.route("/game/<login>", methods=["GET", "POST"])
def game_gate(login):
    error = None

    if request.method == "POST":
        password = request.form.get("password", "")
        if db.verify_password_by_login(login, password):
            if not GAME_BASE_URL:
                return "게임 주소가 아직 안 정해졌다. config.py 의 GAME_BASE_URL 을 확인한다.", 500
            return redirect(f"{GAME_BASE_URL}?{urlencode({'login': login})}")
        error = "비번이 틀렸다. 디스코드에서 `/비밀번호확인` 으로 다시 확인한다."

    return render_template_string(
        GAME_GATE_PAGE,
        login=login,
        error=error,
        **COLORS,
    )


# 디스코드 /연결 명령이 보내준 링크가 오는 자리. state 만 들고 GitHub 로그인 화면으로 보낸다.
@app.route("/login")
def login():
    state = request.args.get("state")
    if not state:
        return "잘못된 링크야. 디스코드에서 /연결 명령으로 다시 받아줘.", 400

    params = urlencode({
        "client_id": os.getenv("GITHUB_OAUTH_CLIENT_ID"),
        "scope": "read:user",
        "state": state,
        "redirect_uri": f"{WEB_BASE_URL}/callback",
    })
    return redirect(f"{GITHUB_OAUTH_AUTHORIZE_URL}?{params}")


# GitHub 이 로그인을 마치고 돌려보내는 자리.
# code 를 진짜 로그인 정보로 바꾸고, state 로 어느 디스코드 유저였는지 되찾는다.
@app.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")

    # state 는 /연결 이 만들어 db 에 넣어둔 값이다. 한 번 쓰면 db.py 가 바로 지운다.
    # 없거나(이미 썼거나) 5분(OAUTH_STATE_EXPIRE_SECONDS)을 넘겼으면 None 이 온다.
    discord_id = db.pop_pending_link(state) if state else None
    if not code or discord_id is None:
        return "연결이 만료됐거나 잘못됐어. 디스코드에서 /연결 명령을 다시 실행해줘.", 400

    token_res = requests.post(
        GITHUB_OAUTH_TOKEN_URL,
        data={
            "client_id": os.getenv("GITHUB_OAUTH_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_OAUTH_CLIENT_SECRET"),
            "code": code,
            "redirect_uri": f"{WEB_BASE_URL}/callback",
        },
        headers={"Accept": "application/json"},
    )
    access_token = token_res.json().get("access_token")
    if not access_token:
        return "GitHub 인증에 실패했어. 디스코드에서 /연결 명령을 다시 실행해줘.", 400

    # 로그인 이름만 확인하면 되니, access_token 은 여기서만 쓰고 저장하지 않는다.
    user_res = requests.get(
        GITHUB_API_USER_URL,
        headers={"Authorization": f"token {access_token}"},
    )
    github_login = user_res.json().get("login")
    if not github_login:
        return "GitHub 계정 정보를 가져오지 못했어.", 400

    db.link_account(discord_id, github_login)
    return f"✅ GitHub 계정 `{github_login}` 이 연결됐어! 디스코드로 돌아가도 돼."


if __name__ == "__main__":
    # debug=True 로 켜면 Flask 가 프로세스를 두 개 띄운다.
    # 감시자(부모)가 파일이 바뀌는지 지켜보다가, 실제로 웹을 돌리는 일꾼(자식)을
    # 껐다 새로 띄운다. 자식에게는 WERKZEUG_RUN_MAIN 이라는 표시가 붙어 있다.
    #
    # 터널은 감시자 쪽에서만 연다. 자식이 다시 떠도 터널은 그대로 살아 있어서,
    # 같은 주소로 두 번 열려다 실패하는 일이 없다.
    # 이렇게 해야 card.py 를 고쳤을 때 web.py 가 알아서 새 코드로 갈아탄다.
    # (예전에는 자동 재시작을 꺼둬서, 카드 디자인을 고쳐도 옛날 그림이 계속 나왔다)
    if os.environ.get("WERKZEUG_RUN_MAIN") is None:
        # authtoken_from_env=True 는 .env 의 NGROK_AUTHTOKEN 을 읽으라는 뜻이다
        # (fetch.py 를 import 할 때 load_dotenv() 가 이미 불려서 값이 올라와 있다).
        #
        # 돌려받은 값을 변수에 담아 둔다. 아무도 안 들고 있으면 파이썬이
        # 필요 없는 값으로 보고 정리해 버려서 터널이 끊긴다.
        listener = ngrok.forward(WEB_PORT, authtoken_from_env=True, domain=NGROK_DOMAIN)
        print(f"공개 주소: {WEB_BASE_URL}  (팀원들도 이 주소로 들어온다)")

    app.run(port=WEB_PORT, debug=True)
