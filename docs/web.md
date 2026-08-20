# web.py

> Flask 웹 페이지. `cache/` 의 JSON 을 읽어 카드를 레벨 순으로 나열한다.

## 역할

| | |
|---|---|
| 입력 | `cache/` 안의 JSON 전부 |
| 출력 | 웹 페이지 (`/` 순위, `/vs/A/B` 두 장 비교) |
| 실행 | `python web.py` → 브라우저에서 `http://127.0.0.1:5000` |

**HTML 은 이 파일 안에 문자열로 둡니다.** `templates/` 폴더를 따로 만들지 않습니다 — 기획서의 파일 구조를 지키기 위해서입니다.

## 실행 방법

```bash
python web.py
```

```
 * Running on http://127.0.0.1:5000
```

브라우저에서:

| 주소 | 화면 |
|---|---|
| `http://127.0.0.1:5000/` | 전체 카드를 레벨 순으로 나열 |
| `http://127.0.0.1:5000/vs/octocat/Spaceghost` | 두 장을 나란히 |

`cache/` 가 비어 있으면 "먼저 `python fetch.py owner/repo` 를 실행한다" 고 안내가 뜹니다.

---

## Flask 짚고 가기

```python
app = Flask(__name__)

@app.route("/")
def index():
    ...
    return render_template_string(PAGE, ...)
```

- `@app.route("/")` — **"이 주소로 들어오면 아래 함수를 불러라"** 는 표시입니다. 데코레이터입니다.
- 함수가 돌려준 문자열이 그대로 브라우저에 그려집니다.
- `render_template_string(PAGE, title="...", people=[...])` — HTML 문자열의 `{{ }}` 자리에 값을 채워 넣습니다.

**`static/` 폴더는 Flask 가 자동으로 웹에 열어줍니다.** `config.py` 의 `CARD_DIR` 이 `"static"` 이라, `card.py` 가 만든 카드가 그냥 주소를 갖게 됩니다. 별도 설정이 필요 없습니다.

```
static/octocat_Hello-World_octocat.png
   → http://127.0.0.1:5000/static/octocat_Hello-World_octocat.png
```

---

## 코드 구조

### `css(color)` — 색 변환

```python
def css(color):
    return f"rgb({color[0]}, {color[1]}, {color[2]})"

COLORS = {"bg": css(CARD_BG), "accent": css(CARD_ACCENT), ...}
```

`config.py` 의 색은 `(18, 18, 20)` 같은 숫자 3개인데 CSS 는 `rgb(18, 18, 20)` 형태를 원합니다. 그걸 바꿔주는 함수입니다.

**색을 여기 직접 적지 않으려고 만든 함수입니다.** 덕분에 `config.py` 만 고치면 **카드와 웹페이지 색이 같이 바뀝니다.**

### `load_people()` — 데이터 준비

```python
for name in sorted(os.listdir(CACHE_DIR)):
    if not name.endswith(".json"):
        continue

    repo = repo_from_cache_name(name)      # 파일명 → 저장소 이름

    for person in load_cache(...):
        stats = calc_stats(person)
        level = calc_level(stats)
        path  = make_card(person, stats, level, repo)   # 카드까지 만든다
        people.append({..., "v": int(os.path.getmtime(path))})

people.sort(key=lambda p: p["level"], reverse=True)
```

**한 함수가 파일 세 개를 순서대로 씁니다.**

```
fetch.load_cache      →  stats.calc_stats/calc_level  →  card.make_card
```

`repo_from_cache_name()` 이 필요한 이유는 **카드 파일명에 저장소 이름이 들어가기 때문**입니다. 여러 저장소를 한 페이지에 올리면 같은 사람이 여러 번 나오는데, 저장소를 안 넣으면 서로 덮어씁니다.

`reverse=True` 로 **레벨 높은 사람부터** 보여줍니다.

### 캐시 방지 쿼리스트링

```python
"v": int(os.path.getmtime(path))
```

```html
<img src="{{ url_for('static', filename=p.file, v=p.v) }}">
<!-- 결과: /static/octocat_Hello-World_octocat.png?v=1787156291 -->
```

**브라우저는 한 번 받은 이미지를 주소가 같으면 다시 받지 않습니다.** 계수를 바꾸고 카드를 새로 만들어도 **옛날 그림이 그대로 보입니다.**

`getmtime()` 은 **파일이 바뀐 시각**입니다. 이걸 주소 뒤에 붙이면 카드가 바뀔 때마다 주소가 달라져서, 브라우저가 "처음 보는 주소" 로 알고 새로 받아갑니다.

> `?v=` 뒤의 값은 이미지 내용과 아무 상관이 없습니다. **주소를 다르게 만드는 것 자체가 목적**입니다.

### `PAGE` — HTML 템플릿

```python
PAGE = """
<!doctype html>
...
  .grid {
    display: grid;
    gap: 20px;
    grid-template-columns: {{ columns }};   /* ★ 여기 한 줄 */
  }
...
"""
```

`{{ }}` 안은 **파이썬이 아니라 Flask 가 채워 넣는 자리**입니다. `{% for %}` `{% if %}` 는 반복과 조건입니다.

**레이아웃의 핵심은 `{{ columns }}` 한 줄입니다.** 이 값만 바꾸면 나열도 되고 두 장 나란히도 됩니다.

| 화면 | columns 값 | 결과 |
|---|---|---|
| `/` | `repeat(auto-fill, minmax(260px, 1fr))` | 화면 폭에 맞춰 몇 장이든 |
| `/vs/A/B` | `repeat(2, minmax(0, 1fr))` | **2칸 고정** |

`auto-fill` 은 "260px 이상이면 한 칸씩 더 넣어라" 라는 뜻입니다. 창을 줄이면 알아서 한 줄에 들어가는 개수가 줄어듭니다.

**HTML 이 한 벌뿐인 게 중요합니다.** 두 화면이 같은 `PAGE` 를 쓰고 값만 다르게 넘깁니다. 나중에 디자인을 고칠 때 한 곳만 고치면 됩니다.

### `/` — 순위

```python
@app.route("/")
def index():
    people = load_people()
    message = None
    if not people:
        message = "cache/ 에 JSON 이 없다. 먼저 python fetch.py owner/repo 를 실행한다."
    return render_template_string(PAGE, ..., columns="repeat(auto-fill, ...)", **COLORS)
```

`**COLORS` 는 딕셔너리를 **인자로 펼쳐 넣는** 문법입니다.

```python
**COLORS   ==   bg="rgb(18,18,20)", accent="rgb(255,176,46)", text=..., ...
```

색이 5개인데 매번 다 적으면 두 함수에 열 줄이 늘어납니다.

### `/vs/<a>/<b>` — 두 장 비교

```python
@app.route("/vs/<a>/<b>")
def vs(a, b):
```

`<a>` `<b>` 는 **주소의 그 자리 값을 함수 인자로 받는다**는 뜻입니다.

```
/vs/octocat/Spaceghost   →   a="octocat", b="Spaceghost"
```

**결투 규칙(승패)은 아직 없습니다.** 레이아웃만 미리 잡아둔 것이라, 지금은 두 장을 골라 나란히 보여주기만 합니다. 기획서의 "확장 예정 — 카드 결투" 를 위한 자리입니다.

찾은 사람만 `picked` 에 담고, 못 찾은 사람은 `missing` 에 모아 화면에 알려줍니다. 한 명만 있어도 그 한 장은 보여줍니다.

### `app.run(debug=True)`

`debug=True` 면 **코드를 고칠 때마다 서버가 알아서 다시 뜹니다.** 개발할 때만 씁니다.

---

## 알고 있어야 할 것

### 새로고침할 때마다 카드를 다시 만든다

`load_people()` 이 매번 `make_card()` 를 부릅니다. **아바타를 매번 다시 다운로드**하기 때문에 9명이면 2~4초쯤 걸립니다.

| | 장점 | 단점 |
|---|---|---|
| **지금 방식** (매번 생성) | `config.py` 계수를 바꾸고 새로고침하면 바로 반영 | 느리다 |
| 파일 있으면 건너뛰기 | 빠르다 | 계수를 바꿔도 반영이 안 된다 |

**밸런스를 맞추는 지금은 지금 방식이 편합니다.** 시연 때 느리면 `make_card` 앞에 "파일이 이미 있으면 건너뛴다" 를 넣으면 됩니다.

### 포트가 이미 쓰이고 있으면

```python
app.run(debug=True, port=5001)
```

`5000` 번이 다른 프로그램에 잡혀 있을 때 바꿉니다.

---

## 이 파일에서 제일 약한 부분

HTML 을 파이썬 문자열로 들고 있는 것입니다. 화면이 조금만 커지면 편집이 괴로워집니다. 다음 단계는 **Flask 의 `templates/` 폴더로 HTML 을 빼는 것**입니다 (파일 구조 규칙을 바꿔야 하므로 팀에 먼저 알립니다).
