# 프로젝트 구성

> 코드 파일 하나당 설명 문서 하나. **이 코드가 무엇을 왜 하는지** 를 적어둔다.

## 문서 목록

### 본 기능 — 기획서의 6개 파일

| 문서 | 파일 | 한 줄 |
|---|---|---|
| [config.md](config.md) | `config.py` | 설정값 보관. 계수·색·크기는 전부 여기에만 |
| [fetch.md](fetch.md) | `fetch.py` | 저장소 주소 → `cache/*.json` |
| [stats.md](stats.md) | `stats.py` | 기여 기록 → 능력치 4개와 레벨 |
| [card.md](card.md) | `card.py` | 능력치 → 600x900 PNG 카드 |
| [bot.md](bot.md) | `bot.py` | `/card` 명령으로 카드를 디스코드에 전송 |
| [web.md](web.md) | `web.py` | 카드를 레벨 순으로 나열 + 두 장 비교 |

### 준비 단계 — 연결 확인용

| 문서 | 파일 | 한 줄 |
|---|---|---|
| [check_github.md](check_github.md) | `check_github.py` | 토큰과 GitHub API 가 되는지 확인 |
| [check_discord.md](check_discord.md) | `check_discord.py` | 봇 접속과 슬래시 명령 등록 확인 |

---

## 데이터 흐름

```
저장소 주소
   │
   ▼
 fetch.py  ──▶  cache/{owner}_{repo}.json
   │              {"login", "avatar", "commits",
   │               "additions", "deletions", "active_weeks"}
   ▼
 stats.py  ──▶  {"ATK": 45, "DEF": 12, "AGI": 66, "STA": 35}, Lv.19
   │
   ▼
 card.py   ──▶  draw_card()  (이미지만)  ──▶  bot.py    디스코드
              └ make_card()  (파일 저장) ──▶  web.py    브라우저

        config.py  ←  위 파일 전부가 설정값을 여기서 가져온다
```

**왼쪽 파일은 오른쪽 파일을 모릅니다.** `fetch.py` 는 카드가 있는지 모르고, `stats.py` 는 디스코드를 모릅니다. 그래서 한 파일씩 따로 작업하고 따로 실행해서 확인할 수 있습니다.

---

## 이 프로젝트를 관통하는 규칙 세 가지

### 1. 데이터 형태는 계약이다

```python
{"login": str, "avatar": str, "commits": int,
 "additions": int, "deletions": int, "active_weeks": int}
```

`fetch.py` 의 `to_our_form()` 이 이 형태를 만들고, 나머지 전부가 이 이름으로 읽습니다. **키 이름을 바꾸면 다른 파일이 조용히 깨집니다.**

### 2. 같은 규칙은 한 곳에만 둔다

파일명 만드는 규칙을 세 파일에 각자 적어뒀다가 사고가 났습니다. 지금은 `fetch.py` 에 한 벌만 있고 나머지가 `import` 해서 씁니다.

```python
normalize_repo()        주소 → owner/repo
cache_path()            owner/repo → 파일 이름
repo_from_cache_name()  파일 이름 → owner/repo
```

### 3. 숫자와 색은 config.py 에만 적는다

동작하는 코드를 안 열고도 밸런스를 조정할 수 있게 하기 위해서입니다. 카드 색을 바꾸려고 `card.py` 를 열었다가 좌표를 건드리면 멀쩡하던 카드가 깨집니다.

---

## 실행 순서 (처음부터 끝까지)

```bash
# 0. 연결 확인 (처음 한 번만)
python check_github.py
python check_discord.py

# 1. 데이터 수집
python fetch.py sclee9961-sys/JAVA

# 2. 계수 확인 (표로)
python stats.py

# 3. 카드 생성 (그림을 눈으로 확인)
python card.py

# 4-a. 디스코드
python bot.py            # 그 뒤 /card 저장소 아이디

# 4-b. 웹
python web.py            # http://127.0.0.1:5000
```

**한 단계씩 결과가 눈에 보이는 것을 확인하고 다음으로 넘어갑니다.**

---

## 다른 문서와의 차이

| 문서 | 무엇이 적혀 있나 |
|---|---|
| **프로젝트구성/** (여기) | **코드가 무엇을 왜 하는지.** 파일별 설명 |
| `docs/기획.md` | 계약서. 데이터 형태·파일 구조·계수 |
| `docs/함정.md` | **실제로 겪은** 문제와 해결. 발표 트러블슈팅 자료 |
| `docs/위험포인트.md` | 아직 안 겪었지만 미리 조사해 둔 주의사항 |
| `docs/연결확인.md` | 팀원용 연결 테스트 사용법 |

막혔을 때 보는 순서: **함정.md → 위험포인트.md → 여기**
