# 기여 기록(fetch.py 가 만든 딕셔너리)을 능력치 4개와 레벨로 바꾼다.
# 계수는 여기 적지 않는다. 전부 config.py 에서 가져다 쓴다.
#
#   python stats.py                       # cache/ 안의 저장소 전부
#   python stats.py octocat/Hello-World   # 한 저장소만

import os
import sys

from config import STAT_WEIGHTS, LEVEL_DIVISOR, STAT_MAX

# fetch.py 의 것을 그대로 쓴다. 읽는 방법을 두 벌 만들면 한쪽만 고치는 실수가 난다.
# load_cache 는 utf-8 을 지정해서 읽는다. 직접 open() 하면 한글 윈도우에서 깨진다.
from fetch import CACHE_DIR, load_cache, normalize_repo, cache_path


# 능력치 4개를 계산한다.
# 어떤 능력치가 어떤 기록에서 나오는지는 여기에 있고, 곱하는 값은 config.py 에 있다.
def calc_stats(person):
    raw = {
        "ATK": person["additions"] * STAT_WEIGHTS["ATK"],
        "DEF": person["deletions"] * STAT_WEIGHTS["DEF"],
        "AGI": person["commits"] * STAT_WEIGHTS["AGI"],
        "STA": person["active_weeks"] * STAT_WEIGHTS["STA"],
    }

    stats = {}
    for name in raw:
        # 1/50 을 곱하면 24.06 같은 소수가 나온다. int() 로 소수점을 버린다.
        # 그리고 STAT_MAX 를 넘지 않게 자른다.
        stats[name] = min(int(raw[name]), STAT_MAX)

    return stats


# 능력치 4개를 더해서 레벨을 낸다.
def calc_level(stats):
    total = sum(stats.values())

    # 기여가 적은 사람은 합이 8 미만이라 Lv.0 이 나온다. 고장난 것처럼 보이니 최소 1로 올린다.
    return max(1, int(total / LEVEL_DIVISOR))


# 한 저장소의 사람들을 표로 찍는다. 계수를 눈으로 보고 조정하려고 만든 것이다.
# 왼쪽은 GitHub 에서 받은 원래 기록, 오른쪽은 환산한 능력치다. 같이 봐야 계수가 보인다.
def print_table(title, people):
    print(f"=== {title}  ({len(people)}명) ===")
    print("login                 커밋     추가     삭제   주 |  ATK  DEF  AGI  STA |  합계   Lv")
    print("-" * 78)

    rows = []
    for p in people:
        stats = calc_stats(p)
        level = calc_level(stats)
        rows.append((p, stats, level))

    # 레벨이 높은 사람부터 보여준다. 보기 편하려고 정렬하는 것뿐이다.
    rows.sort(key=lambda r: r[2], reverse=True)

    levels = []
    for p, stats, level in rows:
        total = sum(stats.values())
        levels.append(level)

        # 능력치가 STAT_MAX 에서 잘렸으면 표시한다. 계수가 너무 큰지 보는 단서다.
        mark = "  <- 상한에 걸림" if max(stats.values()) >= STAT_MAX else ""

        print(
            f"{p['login']:<20}"
            f"{p['commits']:>6}"
            f"{p['additions']:>9}"
            f"{p['deletions']:>9}"
            f"{p['active_weeks']:>5} |"
            f"{stats['ATK']:>5}"
            f"{stats['DEF']:>5}"
            f"{stats['AGI']:>5}"
            f"{stats['STA']:>5} |"
            f"{total:>6}"
            f"{level:>5}"
            f"{mark}"
        )

    return levels


# 아래는 터미널에서 직접 실행했을 때만 돈다. card.py 가 import 할 때는 실행되지 않는다.
if __name__ == "__main__":
    # 인자를 주면 그 저장소만, 없으면 cache/ 안의 파일을 전부 본다.
    if len(sys.argv) > 1:
        # fetch.py 와 똑같은 방법으로 주소를 정리하고 파일명을 만든다.
        # 직접 만들면 URL 을 넣었을 때 https:__github.com_... 이라는 파일을 찾게 된다.
        repo = normalize_repo(sys.argv[1])
        if repo is None:
            print(f"저장소 주소를 알아볼 수 없다: {sys.argv[1]}")
            sys.exit(1)
        names = [os.path.basename(cache_path(repo))]
    else:
        if not os.path.exists(CACHE_DIR):
            print(f"{CACHE_DIR}/ 폴더가 없다. 먼저 python fetch.py owner/repo 를 실행한다.")
            sys.exit(1)
        names = sorted(n for n in os.listdir(CACHE_DIR) if n.endswith(".json"))

    if not names:
        print(f"{CACHE_DIR}/ 에 JSON 이 없다. 먼저 python fetch.py owner/repo 를 실행한다.")
        sys.exit(1)

    all_levels = []

    for name in names:
        path = os.path.join(CACHE_DIR, name)
        if not os.path.exists(path):
            print(f"{path} 가 없다. 먼저 python fetch.py 로 받는다.")
            continue

        people = load_cache(path)
        all_levels += print_table(name, people)
        print()

    # 계수를 조정할 때 볼 값.
    if all_levels:
        avg = sum(all_levels) // len(all_levels)
        print(f"전체 {len(all_levels)}명 | 레벨 {min(all_levels)} ~ {max(all_levels)} (평균 {avg})")
        print("기획서 조정 기준: 여러 저장소를 넣어보며 레벨이 20~50 사이에 떨어지게 맞춘다.")
        print("전체가 낮거나 높으면 config.py 의 LEVEL_DIVISOR 를 먼저 조절한다.")
