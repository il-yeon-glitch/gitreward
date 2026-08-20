# check_github.py

> GitHub 연결 확인용. **본 기능이 아니라 준비 단계 스크립트다.**

## 역할

| | |
|---|---|
| 입력 | 저장소 주소 (없으면 `octocat/Hello-World`) |
| 출력 | 응답을 그대로 화면에 (파일 저장 안 함) |
| 실행 | `python check_github.py` |

두 가지만 봅니다.

1. **토큰이 살아 있나**
2. **참여자 통계를 받아올 수 있나**

**받은 응답에서 값을 꺼내지 않습니다.** 구조를 눈으로 보는 게 목적입니다.

> 기획서의 파일 구조(`config`/`fetch`/`stats`/`card`/`bot`/`web`) 밖에 있는 파일입니다. 코드를 짜기 전에 **"내 환경에서 되는가" 를 먼저 확인**하려고 만들었습니다. 본 기능이 완성된 지금도 남겨둡니다 — 새 팀원이 합류하거나 토큰이 만료됐을 때 제일 먼저 돌려볼 파일입니다.

## 실행 방법

```bash
python check_github.py                       # 기본값 octocat/Hello-World
python check_github.py sclee9961-sys/JAVA    # 저장소 지정
```

**정상 출력:**

```
확인할 저장소: octocat/Hello-World

[1단계] 토큰 확인
  GET https://api.github.com/user
  응답 코드: 200
  토큰 주인: sclee9961-sys
  남은 요청 횟수: 4998 / 5000  (5000 이면 토큰이 붙은 것, 60 이면 안 붙은 것)

[2단계] 참여자 통계 요청
  GET https://api.github.com/repos/octocat/Hello-World/stats/contributors
  1번째 시도 -> 200 (본문 1573바이트)

[3단계] 받은 응답
  응답 코드: 200
  크기: 1573바이트
------------------------------------------------------------
[
  {
    "total": 1,
    "weeks": [ { "w": 1367712000, "a": 0, "d": 0, "c": 0 }, ... ],
    "author": { "login": "Spaceghost", "avatar_url": "https://...", ... }
  }
]
```

---

## 왜 이 파일이 필요했나

코드를 짜기 전에 **모르는 것을 없애기 위해서**입니다.

`fetch.py` 를 바로 만들었으면 "카드가 안 나온다" 는 결과만 보고 원인을 찾아야 합니다. 토큰이 틀린 건지, API 주소가 틀린 건지, 응답 구조를 잘못 읽은 건지 구분이 안 됩니다.

**단계를 나눠서 어디까지 되는지 먼저 확인하면** 그 다음부터는 확실한 땅 위에서 코드를 짤 수 있습니다.

---

## 코드 구조

### `make_headers()`

```python
def make_headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"}
```

**토큰 값 자체는 어디에도 출력하지 않습니다.** 화면에 찍으면 발표 화면 캡처나 녹화에 남습니다.

### 1단계 — `check_token(headers)`

```python
res = requests.get(f"{API}/user", headers=headers)
```

`/user` 는 **"이 토큰의 주인이 누구냐"** 를 묻는 주소입니다. 권한 체크를 하나도 안 준 토큰이어도 답해줍니다. 그래서 **토큰이 살아 있는지 확인하는 가장 싼 방법**입니다.

| 응답 | 뜻 |
|---|---|
| 200 | 토큰 정상. `login` 에 주인 아이디가 온다 |
| 401 | 토큰이 잘못됐거나 만료됨 |

```python
remaining = res.headers.get("X-RateLimit-Remaining")
limit = res.headers.get("X-RateLimit-Limit")
```

**이 두 줄이 은근히 중요합니다.** 토큰이 제대로 붙었으면 **5000**, 안 붙었으면 **60** 이 옵니다.

토큰을 잘못 적어도 GitHub 은 공개 저장소라면 그냥 답해줍니다. 그래서 **"되는 것 같은데 사실 토큰 없이 도는 중"** 인 상태가 생깁니다. 나중에 60회를 다 쓰고 갑자기 막히는데, 이 숫자를 보면 미리 알 수 있습니다.

### 2단계 — `get_contributor_stats(repo, headers)`

**이 프로젝트의 대표 함정이 여기 있습니다.**

```python
for i in range(1, RETRY_MAX + 1):
    res = requests.get(url, headers=headers)
    size = len(res.content)
    print(f"  {i}번째 시도 -> {res.status_code} (본문 {size}바이트)")

    if res.status_code == 202:
        print(f"     202: 아직 계산 중이고 본문이 비어 있다. {RETRY_WAIT}초 기다렸다 다시 물어본다.")
        time.sleep(RETRY_WAIT)
        continue
```

`/stats/contributors` 는 GitHub 이 통계를 **미리 계산해 두는** 방식입니다. 계산이 안 돼 있으면:

```
1번째 시도 -> 202 (본문 2바이트)      ← {} 만 옴
   202: 아직 계산 중이고 본문이 비어 있다. 2초 기다렸다 다시 물어본다.
2번째 시도 -> 200 (본문 4218바이트)   ← 이제 진짜 데이터
```

**본문 바이트 수를 찍는 게 핵심입니다.** 202 라는 숫자만 보면 "뭔가 왔나 보다" 하고 넘어가기 쉬운데, `2바이트` 를 보면 **정말 비어 있다는 걸 눈으로 확인**하게 됩니다.

`if size == 0` 검사는 커밋이 없는 새 저장소용입니다. 없으면 다음 단계의 `res.json()` 이 터집니다.

### 3단계 — `print_response(res)`

```python
print(json.dumps(res.json(), indent=2, ensure_ascii=False))
```

**값을 꺼내거나 키 이름을 바꾸지 않습니다.** 줄바꿈(`indent=2`)과 한글 처리(`ensure_ascii=False`)만 넣습니다.

이 출력을 보고 **기획서의 데이터 형태와 어떻게 연결되는지** 확인합니다.

| GitHub 응답 | → | 우리 형태 |
|---|---|---|
| `author.login` | → | `login` |
| `author.avatar_url` | → | `avatar` (**이름이 다르다**) |
| `total` | → | `commits` |
| `weeks[].a` 를 전부 더함 | → | `additions` |
| `weeks[].d` 를 전부 더함 | → | `deletions` |
| `weeks[]` 중 `c > 0` 인 개수 | → | `active_weeks` |

**합계 필드가 없다는 걸 여기서 알게 됩니다.** `weeks` 배열을 직접 더해야 합니다. 이걸 미리 봤기 때문에 `fetch.py` 의 `to_our_form()` 을 헤매지 않고 짤 수 있었습니다.

---

## 이 파일에는 없는 것

`fetch.py` 와 달리 **주소 정리(`normalize_repo`)가 없습니다.** `owner/repo` 형태로 정확히 넣어야 합니다. 확인용이라 그 정도면 충분합니다.

## 겪은 함정

- **`ModuleNotFoundError: No module named 'dotenv'`** — 패키지 이름은 `python-dotenv` 인데 import 이름은 `dotenv` 라 설치가 안 된 걸 놓쳤습니다. → `pip install python-dotenv`
- **다른 폴더에서 실행하니 401** — `load_dotenv()` 는 실행 위치(cwd)가 아니라 **스크립트 파일이 있는 폴더** 기준으로 `.env` 를 찾습니다. → 프로젝트 폴더 안에서 실행합니다.
- **유명한 저장소는 202 가 안 뜹니다.** 이미 계산돼 있기 때문입니다. `octocat/Hello-World` 는 바로 200 이 옵니다. 202 를 직접 보고 싶으면 **아무도 안 본 작은 저장소**를 넣어야 합니다.
