# fetch.py

> 저장소 주소를 받아 참여자별 기여 기록을 모아 `cache/` 에 JSON 으로 저장한다.

## 역할

| | |
|---|---|
| 입력 | 저장소 주소 (`facebook/react` 또는 `https://github.com/facebook/react`) |
| 출력 | `cache/{owner}_{repo}.json` + 딕셔너리 리스트 |
| 실행 | `python fetch.py facebook/react` |

**능력치로 바꾸는 일은 여기서 하지 않습니다.** 그건 `stats.py` 가 할 일입니다. 이 파일은 "GitHub 에서 받아와 우리 형태로 정리해 저장" 까지만 합니다.

## 이 파일이 특별한 이유

`fetch.py` 는 데이터를 받아오는 파일이면서 동시에 **이 프로젝트의 규칙 저장소**입니다.

```
normalize_repo()        주소 정리 규칙
cache_path()            저장소 이름 → 파일 이름
repo_from_cache_name()  파일 이름 → 저장소 이름
```

이 세 개를 `stats.py`, `card.py`, `web.py` 가 **import 해서 가져다 씁니다.** 각자 만들지 않습니다. (실제로 각자 만들었다가 사고가 났습니다 — 아래 "겪은 함정" 참고)

---

## 실행 방법

```bash
python fetch.py facebook/react
python fetch.py https://github.com/facebook/react     # 주소 형태도 됨
```

**정상 출력:**

```
GitHub 에 요청한다: sclee9961-sys/JAVA
  1번째 시도: 202 (아직 계산 중) - 2초 뒤에 다시 요청한다
저장했다: cache\sclee9961-sys_JAVA.json
참여자 3명
  sclee9961-sys        커밋    42  +9576    -225     6주
```

**두 번째 실행부터는 API 를 안 부릅니다:**

```
캐시를 읽는다: cache\sclee9961-sys_JAVA.json
```

새로 받고 싶으면 **그 JSON 파일을 지우고** 다시 실행합니다.

---

## 코드 구조

### `normalize_repo(text)` — 주소 정리

어떤 형태로 넣어도 `owner/repo` 로 만듭니다.

```
https://github.com/facebook/react       →  facebook/react
https://github.com/facebook/react.git   →  facebook/react
https://github.com/facebook/react/      →  facebook/react
github.com/facebook/react/tree/main     →  facebook/react
facebook/react                          →  facebook/react
알아볼 수 없음                            →  None
```

시연 때 팀원이 주소를 **어떤 형태로 넣을지 모르기 때문에** 만든 함수입니다. 브라우저 주소창에서 복붙하면 `https://` 가 붙어 오고, `git clone` 주소를 복붙하면 `.git` 이 붙어 옵니다.

```python
s = s.rstrip("/")           # 순서가 중요하다.
if s.endswith(".git"):      # ".git/" 처럼 둘 다 붙어 있을 수 있어서
    s = s[:-4]              # / 를 먼저 뗀다
```

마지막에 `s.split("/")` 의 **앞 두 조각만** 씁니다. 그래서 뒤에 `/tree/main` 같은 게 붙어 있어도 알아서 잘립니다.

### `cache_path(repo)` — 파일 이름 만들기

```python
def cache_path(repo):
    return os.path.join(CACHE_DIR, repo.replace("/", "_") + ".json")
```

`facebook/react` → `cache/facebook_react.json`

**`/` 를 `_` 로 바꾸는 게 핵심입니다.** 그대로 쓰면 `cache/facebook/react.json` 이 되어서, `facebook` 폴더가 없다며 실패합니다.

### `repo_from_cache_name(name)` — 그 반대

```python
def repo_from_cache_name(name):
    return name[:-len(".json")].replace("_", "/", 1)
```

`octocat_Hello-World.json` → `octocat/Hello-World`

**`replace(..., 1)` 의 마지막 인자 `1` 이 중요합니다.** "첫 번째 것만 바꿔라" 라는 뜻입니다. `Hello-World` 대신 `Hello_World` 같은 저장소 이름이 오면 `_` 가 여러 개인데, GitHub 아이디에는 `_` 가 들어갈 수 없으니 **첫 번째 `_` 가 owner 와 repo 의 구분점**입니다.

### `save_cache()` / `load_cache()`

```python
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

세 가지가 다 필요합니다.

| 빠뜨리면 | 무슨 일이 나나 |
|---|---|
| `os.makedirs(CACHE_DIR, exist_ok=True)` | 폴더가 없어서 파일을 못 만든다 |
| `encoding="utf-8"` | 한글 윈도우의 기본은 cp949 라 한글이 깨진다 |
| `ensure_ascii=False` | 한글이 `\uc548\ub155` 처럼 저장돼 열어봐도 못 읽는다 |

> `exist_ok=True` 는 "이미 있어도 에러 내지 말고 넘어가라" 는 뜻입니다.

### `get_stats(repo, headers)` — API 호출과 재시도

**이 함수가 이 파일에서 제일 조심스러운 부분입니다.** GitHub 이 여러 가지로 답하기 때문입니다.

```python
for i in range(1, RETRY_MAX + 1):
    res = requests.get(url, headers=headers)

    if res.status_code == 202:      # 아직 계산 중 → 2초 쉬고 재시도
        time.sleep(RETRY_WAIT)
        continue
    if res.status_code == 404:      # 없거나 비공개
        return None
    if res.status_code in (403, 429):   # 요청 횟수 초과
        return None
    if res.status_code == 204 or not res.content:   # 커밋 없는 저장소
        return None
    if res.status_code != 200:
        return None
    return res.json()
```

**202 가 이 API 의 대표적인 함정입니다.** `/stats/contributors` 는 GitHub 이 통계를 미리 계산해 두는 방식이라, 계산이 안 돼 있으면 **202 와 빈 본문**을 주고 "계산 시작했으니 잠깐 뒤에 다시 물어봐라" 합니다. 이걸 모르고 `res.json()` 을 바로 부르면 터집니다.

`RETRY_MAX = 5` 상한이 있는 이유는, 상한이 없으면 커밋 없는 저장소에서 **반복문이 영원히 끝나지 않기** 때문입니다.

`204 or not res.content` 검사가 없으면 그 다음 줄의 `res.json()` 이 빈 본문을 파싱하려다 터집니다.

### `to_our_form(raw)` — 형태 변환

GitHub 응답을 **기획서가 정한 데이터 형태로** 옮깁니다. 여기가 이 프로젝트의 계약을 지키는 자리입니다.

```python
{"login": str, "avatar": str, "commits": int,
 "additions": int, "deletions": int, "active_weeks": int}
```

**키 이름을 바꾸면 안 됩니다.** 다른 파일 전부가 이 이름으로 읽습니다. 특히 `avatar_url` 이 아니라 **`avatar`** 입니다 — 그대로 두면 `card.py` 가 못 읽습니다.

```python
if c["author"] is None:
    continue
```

커밋 이메일이 GitHub 계정과 연결돼 있지 않으면 `author` 가 `None` 으로 옵니다. 그냥 두면 다음 줄의 `c["author"]["login"]` 이 `TypeError` 로 터집니다.

```python
for w in c["weeks"]:
    additions += w["a"]      # a = added
    deletions += w["d"]      # d = deleted
    if w["c"] > 0:           # c = commits
        active_weeks += 1
```

GitHub 응답에는 **추가/삭제 줄 수의 합계 필드가 없습니다.** 주 단위 값이 배열로 오기 때문에 직접 더해야 합니다. 그리고 `weeks` 배열에는 커밋이 0인 주도 전부 들어 있어서, **커밋이 한 번이라도 있는 주만** 활동한 주로 셉니다.

### `get_contributors(repo_text)` — 입구

**다른 파일이 부르는 함수는 이것 하나입니다.** `bot.py` 도 `web.py`(간접적으로) 도 이걸 씁니다.

```
주소 정리  →  캐시 있나?  →  있으면 그걸 읽고 끝
                 없으면 ↓
            토큰 확인  →  API 호출  →  형태 변환  →  저장
```

**캐시를 먼저 보는 게 중요합니다.** 요청 횟수를 아끼기도 하지만, **시연 때 와이파이가 끊겨도 돌아가기 때문**입니다. 발표 전에 미리 `python fetch.py` 를 돌려 두면 안전합니다.

```python
headers = {"Authorization": f"Bearer {token}", ...}
```

토큰 없이 부르면 시간당 60회에서 막히고, 붙이면 5000회입니다.

### `if __name__ == "__main__":`

이 줄 아래는 **터미널에서 직접 실행했을 때만** 돕니다. `bot.py` 가 `import fetch` 할 때는 실행되지 않습니다.

**이 줄이 없으면 import 만 해도 아래 코드가 전부 돌아버립니다.** 봇을 켜자마자 "사용법: python fetch.py owner/repo" 가 뜨고 종료되는 상황이 됩니다.

---

## 겪은 함정

- **대형 저장소는 추가/삭제가 0으로 옵니다.** `facebook/react` 를 넣으면 500명 전원의 `additions`/`deletions` 가 0입니다. GitHub 원본 응답의 주별 `a`·`d` 가 전부 0으로 오는 것이고 **우리 합산 버그가 아닙니다** (`commits` 와 `active_weeks` 는 정상). → **시연에는 팀 저장소를 씁니다.**
- **202 재시도가 실제로 발동했습니다.** 2초 대기 1회로 200 을 받았습니다. 유명한 저장소는 이미 캐시돼 있어서 202 가 안 뜹니다.
- **`load_dotenv()` 는 실행 위치(cwd)가 아니라 스크립트가 있는 폴더 기준으로 `.env` 를 찾습니다.** 다른 폴더에서 실행하면 401 이 납니다.

## 알아둘 것

- 코드 주석에 "상위 100명까지만 온다" 고 적혀 있는데, 실제로는 `facebook/react` 에서 **500명이 왔습니다.** 팀 저장소는 어느 쪽이든 문제없습니다.
