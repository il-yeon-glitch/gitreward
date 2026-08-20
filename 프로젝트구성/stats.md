# stats.py

> 기여 기록을 능력치 4개와 레벨로 바꾼다.

## 역할

| | |
|---|---|
| 입력 | `fetch.py` 가 만든 딕셔너리 한 개 |
| 출력 | 능력치 딕셔너리 `{"ATK": 45, "DEF": 12, "AGI": 66, "STA": 35}` 와 레벨 `int` |
| 실행 | `python stats.py` (전체) / `python stats.py owner/repo` (한 저장소) |

**이 프로젝트에서 제일 짧은 파일입니다.** 실제 계산은 함수 두 개, 15줄이 전부입니다. 나머지는 계수를 눈으로 보려고 만든 표 출력입니다.

## 실행 방법

```bash
python stats.py                       # cache/ 안의 저장소 전부
python stats.py octocat/Hello-World   # 한 저장소만
```

**출력:**

```
=== sclee9961-sys_JAVA.json  (3명) ===
login                 커밋     추가     삭제   주 |  ATK  DEF  AGI  STA |  합계   Lv
------------------------------------------------------------------------------
sclee9961-sys           42     9576      225    6 |  99    4   84   30 |   217   27
...

전체 9명 | 레벨 1 ~ 31 (평균 10)
기획서 조정 기준: 여러 저장소를 넣어보며 레벨이 20~50 사이에 떨어지게 맞춘다.
```

**왼쪽은 GitHub 에서 받은 원래 기록, 오른쪽은 환산한 능력치입니다.** 둘을 같이 봐야 계수가 적절한지 판단할 수 있습니다. "커밋 42개가 AGI 84 인 게 맞나?" 를 눈으로 보는 것이 이 표의 목적입니다.

---

## 코드 구조

### `calc_stats(person)` — 능력치 4개

```python
def calc_stats(person):
    raw = {
        "ATK": person["additions"]    * STAT_WEIGHTS["ATK"],
        "DEF": person["deletions"]    * STAT_WEIGHTS["DEF"],
        "AGI": person["commits"]      * STAT_WEIGHTS["AGI"],
        "STA": person["active_weeks"] * STAT_WEIGHTS["STA"],
    }

    stats = {}
    for name in raw:
        stats[name] = min(int(raw[name]), STAT_MAX)
    return stats
```

**어떤 능력치가 어떤 기록에서 나오는지는 여기 있고, 곱하는 값은 `config.py` 에 있습니다.**

이 구분이 중요합니다. "ATK 는 추가한 줄 수에서 나온다" 는 **기획**이라 잘 안 바뀌지만, "1/50 을 곱한다" 는 **밸런스**라 자주 바뀌기 때문입니다. 자주 바뀌는 것만 밖에 빼둔 것입니다.

마지막 줄이 두 가지를 한꺼번에 합니다.

```python
min(int(raw[name]), STAT_MAX)
     └─ 소수점 버리기    └─ 99 넘지 않게 자르기
```

`9576 × 1/50 = 191.52` 라는 소수가 나옵니다. `int()` 로 191 이 되고, `min(191, 99)` 로 **99 에서 잘립니다.**

> `int()` 는 반올림이 아니라 **버리기**입니다. `191.9` 도 191 이 됩니다. 능력치는 정수로 보여야 하고, 0.5 차이는 카드에서 의미가 없어서 버리는 쪽을 골랐습니다.

### `calc_level(stats)` — 레벨

```python
def calc_level(stats):
    total = sum(stats.values())
    return max(1, int(total / LEVEL_DIVISOR))
```

**`max(1, ...)` 이 필요한 이유:** 기여가 적은 사람은 능력치 합이 8 미만이라 `Lv.0` 이 나옵니다. 숫자로는 맞지만 **고장난 것처럼 보입니다.** 최소 1로 올려서 "적게 했지만 참여는 했다" 로 보이게 합니다.

`sum(stats.values())` 는 딕셔너리의 **값들만** 더합니다. `{"ATK": 99, "DEF": 4, ...}` 에서 `99 + 4 + ...` 를 구하는 것입니다.

### `print_table(title, people)` — 확인용 표

계산이 아니라 **눈으로 보기 위한** 함수입니다. 세 가지를 합니다.

1. **레벨 높은 순으로 정렬** — `rows.sort(key=lambda r: r[2], reverse=True)`
2. **상한에 걸린 사람 표시** — `<- 상한에 걸림`
3. **레벨 목록을 돌려줌** — 마지막에 전체 범위와 평균을 내려고

```python
mark = "  <- 상한에 걸림" if max(stats.values()) >= STAT_MAX else ""
```

이 표시가 있으면 **계수가 너무 큰지 알 수 있습니다.** 여러 명이 동시에 99 에 걸려 있으면 능력치 차이가 안 보인다는 뜻이라, 계수를 줄여야 합니다.

```python
f"{p['login']:<20}"      # 왼쪽 정렬, 20칸
f"{p['commits']:>6}"     # 오른쪽 정렬, 6칸
```

`:<20` 은 왼쪽 정렬, `:>6` 은 오른쪽 정렬입니다. 숫자를 오른쪽 정렬해야 자릿수가 맞아서 표로 읽힙니다.

### 마지막 요약

```python
avg = sum(all_levels) // len(all_levels)
print(f"전체 {len(all_levels)}명 | 레벨 {min} ~ {max} (평균 {avg})")
```

`//` 는 나눈 뒤 소수점을 버리는 나눗셈입니다. `/` 를 쓰면 `10.333...` 이 나옵니다.

**이 한 줄이 밸런스 조정의 기준입니다.** 여기 나온 범위가 20~50 안에 들어오면 계수를 안 건드려도 됩니다.

---

## 다른 파일과의 관계

```python
from config import STAT_WEIGHTS, LEVEL_DIVISOR, STAT_MAX
from fetch import CACHE_DIR, load_cache, normalize_repo, cache_path
```

**`fetch.py` 의 함수를 가져다 씁니다. 직접 만들지 않습니다.**

- `load_cache` — 직접 `open()` 하면 한글 윈도우에서 깨집니다. `utf-8` 을 지정해서 읽는 함수가 이미 있습니다.
- `normalize_repo` / `cache_path` — 파일 이름 만드는 규칙. 직접 만들었다가 사고가 났습니다(아래 참고).

## 겪은 함정

- **`python fetch.py <URL>` 로 분명히 받았는데 `stats.py` 가 "파일이 없다" 고 했습니다.** 파일명 만드는 규칙을 세 파일에 각자 적어둬서, 주소를 정리하는 `normalize_repo()` 가 `fetch.py` 에만 있었던 것입니다. `stats.py` 는 URL 을 그대로 `_` 로 바꿔 `cache\https:__github.com_....json` 이라는 엉뚱한 파일을 찾고 있었습니다.
  → `fetch.py` 것을 가져다 쓰게 고쳤습니다. **같은 규칙은 한 곳에만 둡니다.**
  (에러 메시지가 "먼저 fetch.py 로 받는다" 라고 해서 원인을 엉뚱한 데서 찾게 만든 것도 함정이었습니다)

- **레벨이 `1~17` 로 나와 계수가 잘못된 줄 알고 고치려 했습니다.** 표본이 `octocat/Hello-World`(커밋 1개) 같은 장난 저장소뿐이었던 게 원인이었습니다. 진짜 팀 저장소를 넣으니 `Lv.19~31` 로 정상이었습니다.
  → **설정을 의심하기 전에 넣은 데이터가 대표성이 있는지 먼저 봅니다.**
