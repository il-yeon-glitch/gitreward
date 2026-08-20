# card.py

> 능력치를 받아 600x900 RPG 카드 PNG 를 만든다.

## 역할

| | |
|---|---|
| 입력 | 사람 딕셔너리 + 능력치 + 레벨 (+ 저장소 이름) |
| 출력 | `Image` 객체 또는 `static/{owner}_{repo}_{login}.png` |
| 실행 | `python card.py` (전체) / `python card.py owner/repo` (한 저장소) |

**색과 크기는 이 파일에 적지 않습니다.** 전부 `config.py` 에서 가져옵니다.

## 실행 방법

```bash
python card.py                              # cache/ 안의 저장소 전부
python card.py il-yeon-glitch/askme-project # 한 저장소만
```

```
=== sclee9961-sys_JAVA.json ===
  static\sclee9961-sys_JAVA_sclee9961-sys.png  (Lv.27  {'ATK': 99, ...})

카드 9장을 static/ 에 만들었다.
```

만든 뒤 `static/` 폴더를 열어 **그림을 직접 봅니다.** 글자가 네모(□□□)로 나오지 않는지가 제일 중요합니다.

---

## 함수가 두 개로 나뉜 이유

이 파일에서 제일 중요한 설계입니다.

```python
def draw_card(person, stats, level):        # 그리기만 한다. 저장 안 함
    ...
    return card

def make_card(person, stats, level, repo):  # 그린 뒤 static/ 에 저장
    card = draw_card(person, stats, level)
    card.save(path)
    return path
```

| 함수 | 누가 쓰나 | 왜 |
|---|---|---|
| `draw_card()` | **bot.py** | 디스코드는 파일을 안 거치고 메모리로 바로 보낸다 |
| `make_card()` | **web.py**, `python card.py` | 웹은 `<img>` 로 보여줘야 해서 파일이 필요하다 |

봇이 카드를 보낼 때마다 디스크에 파일이 쌓이면 곤란합니다. 반대로 웹은 파일 주소가 있어야 브라우저가 그림을 가져갈 수 있습니다. **필요한 쪽이 다르니 함수를 나눴습니다.**

---

## 코드 구조

### `load_avatar(url)` — 프로필 이미지

```python
res = requests.get(url)
img = Image.open(BytesIO(res.content)).convert("RGB")
return img.resize((AVATAR_SIZE, AVATAR_SIZE))
```

`res.content` 는 이미지의 **바이트 덩어리**입니다. `Image.open()` 은 원래 파일을 여는 함수라 "파일처럼 생긴 것" 을 원합니다. `BytesIO` 가 바이트 덩어리를 **파일인 척** 감싸주는 역할을 합니다. 그래서 디스크에 저장하지 않고 바로 열 수 있습니다.

`.convert("RGB")` 는 형식을 통일하는 것입니다. GitHub 아바타가 PNG(투명 있음)로 올 수도, JPEG 로 올 수도 있는데 그대로 붙이면 배경이 이상해집니다.

### `make_circle_mask(size)` — 원형 자르기

```python
def make_circle_mask(size):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask
```

**마스크는 이미지를 자르는 게 아니라, 붙일 때 어디를 붙일지 알려주는 흑백 그림입니다.**

```
마스크(L 모드)           결과
┌─────────┐            ┌─────────┐
│  ◜███◝  │  흰색=255   │  ◜사진◝  │  흰 부분만
│ ███████ │  → 붙는다   │ ██사진██ │  붙는다
│  ◟███◞  │            │  ◟사진◞  │
│▓       ▓│  검정=0     │▓ 배경  ▓│  검은 부분은
└─────────┘  → 안 붙음  └─────────┘  배경이 그대로
```

- `"L"` 은 **흑백 한 채널** 모드입니다. 색이 필요 없고 0~255 밝기만 있으면 됩니다.
- `ellipse()` 는 사각형 안에 꽉 찬 타원을 그립니다. **정사각형에 그리면 원이 됩니다.**
- `size - 1` 인 이유는 좌표가 0부터 시작하기 때문입니다. 200 크기면 0~199 입니다.

```python
card.paste(avatar, (avatar_x, AVATAR_TOP), make_circle_mask(AVATAR_SIZE))
                                            └─ 세 번째 인자가 마스크
```

### 아바타 실패 처리

```python
try:
    avatar = load_avatar(person["avatar"])
except Exception as e:
    print(f"  아바타를 못 받았다: {e}")
    avatar = Image.new("RGB", (AVATAR_SIZE, AVATAR_SIZE), CARD_BAR_BG)
```

**시연 중에 와이파이가 끊겨도 카드는 나오게 합니다.** 사진 대신 회색 원이 들어갑니다.

다만 `except: pass` 로 조용히 넘기지 않고 **원인을 화면에 남깁니다.** 아무 말 없이 회색 원이 나오면 "왜 이러지" 하고 한참 헤매게 됩니다.

### 글자 — anchor

```python
draw.text((CARD_WIDTH // 2, NAME_TOP), person["login"],
          font=font_name, fill=CARD_TEXT, anchor="mm")
```

`anchor` 는 **"이 좌표가 글자의 어디냐"** 를 정합니다.

| anchor | 뜻 | 쓰는 곳 |
|---|---|---|
| `"mm"` | middle-middle (한가운데) | 이름, 레벨 — 카드 정중앙 |
| `"lm"` | left-middle (왼쪽 중간) | 능력치 이름 — 왼쪽 정렬 |
| `"rm"` | right-middle (오른쪽 중간) | 능력치 값 — 오른쪽 정렬 |

**이게 없으면 글자 폭을 직접 재서 가운데를 맞춰야 합니다.** 이름 길이가 사람마다 다르니 `octocat` 과 `il-yeon-glitch` 의 시작 위치가 달라야 하는데, `anchor="mm"` 이 알아서 해줍니다.

### 폰트

```python
font_name  = ImageFont.truetype(FONT_PATH, FONT_SIZE_NAME)
font_level = ImageFont.truetype(FONT_PATH, FONT_SIZE_LEVEL)
font_stat  = ImageFont.truetype(FONT_PATH, FONT_SIZE_STAT)
```

**크기별로 따로 불러와야 합니다.** 한 번 만든 폰트 객체의 크기는 나중에 못 바꿉니다.

`ImageFont.truetype()` 대신 기본 폰트를 쓰면 **한글이 네모(□□□)로 나옵니다.**

### 능력치 막대

```python
for key in STAT_NAMES:
    value = stats[key]
    ...
    # 1) 빈 막대를 먼저 깐다
    draw.rectangle([...], fill=CARD_BAR_BG)

    # 2) 그 위에 값만큼 덮는다
    ratio = min(value / BAR_MAX, 1.0)
    if ratio > 0:
        draw.rectangle([... int(bar_width * ratio) ...], fill=CARD_ACCENT)

    y += STAT_ROW_HEIGHT
```

**막대를 두 번 그리는 이유:** 빈 막대(회색)가 있어야 "얼마나 안 찼는지" 가 보입니다. 채워진 부분만 그리면 짧은 막대가 그냥 짧은 선으로 보입니다.

`min(value / BAR_MAX, 1.0)` — 능력치가 `BAR_MAX`(100)를 넘어도 **막대가 카드 밖으로 나가지 않게** 1.0 에서 자릅니다.

`if ratio > 0` — 능력치가 0이면 막대를 아예 안 그립니다. 안 그러면 폭 0짜리 사각형이 얇은 선으로 남습니다.

`y += STAT_ROW_HEIGHT` — 한 줄 그릴 때마다 아래로 내려갑니다. **`for key in STAT_NAMES:` 의 순서가 그대로 카드 순서**입니다.

### `make_card()` — 파일 이름

```python
name = f"{repo.replace('/', '_')}_{person['login']}.png"
# il-yeon-glitch/askme-project + il-yeon-glitch
#   -> il-yeon-glitch_askme-project_il-yeon-glitch.png
```

**저장소 이름을 파일명에 넣는 게 핵심입니다.** 아이디만 쓰면 같은 사람이 여러 저장소에 있을 때 나중 카드가 앞의 것을 덮어씁니다. (실제로 겪었습니다 — 아래 참고)

---

## 겪은 함정

- **"카드 8장을 만들었다" 는데 `static/` 에 파일이 6개뿐이었습니다.** 저장 경로가 `static/{login}.png` 라서, 같은 사람이 여러 저장소에 있으면 **나중에 만든 카드가 앞의 것을 덮어쓴** 것입니다. `il-yeon-glitch` 가 저장소 3개에 있어 Lv.19 → Lv.17 → Lv.31 순으로 덮였습니다.
  → `make_card(person, stats, level, repo)` 로 인자를 하나 늘리고 파일명을 `{owner}_{repo}_{login}.png` 로 바꿨습니다. 되돌리는 규칙 `repo_from_cache_name()` 은 `fetch.py` 에 한 개만 둡니다.

- **`python card.py <URL>` 이 파일을 못 찾았습니다.** `stats.py` 와 같은 원인이었습니다. `fetch.py` 의 `normalize_repo()` / `cache_path()` 를 가져다 쓰게 고쳤습니다.

## 알아둘 것

- 배치를 바꾸려면 `config.py` 의 `*_TOP`, `STAT_ROW_HEIGHT` 를 만집니다. **이 파일을 열 필요가 없습니다.**
- 능력치를 하나 늘리려면 `STAT_NAMES` 에 추가하고 `CARD_HEIGHT` 나 `STAT_ROW_HEIGHT` 를 조정해야 합니다. 자동으로 안 맞춰집니다.
