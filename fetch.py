# 저장소 주소를 받아 참여자별 기여 기록을 모아 cache/ 에 JSON 으로 저장한다.
# 능력치로 바꾸는 일은 여기서 하지 않는다. stats.py 가 할 일이다.
#
#   python fetch.py facebook/react
#   python fetch.py https://github.com/facebook/react

import os
import sys
import json
import time

import requests
from dotenv import load_dotenv

# .env 에 적어둔 값을 환경변수로 불러온다.
# os.getenv() 는 .env 를 자동으로 읽지 않는다. 이 줄이 먼저 와야 한다.
load_dotenv()

API = "https://api.github.com"

# 받아온 JSON 을 넣어둘 폴더.
CACHE_DIR = "cache"

# 202(아직 계산 중) 가 오면 잠깐 쉬었다가 다시 물어본다.
# 상한이 없으면 커밋 없는 저장소에서 반복문이 끝나지 않는다.
RETRY_MAX = 5
RETRY_WAIT = 2


# 어떤 형태로 넣어도 "owner/repo" 로 정리한다.
# 시연 때 팀원이 주소를 어떤 형태로 넣을지 모른다.
#
#   https://github.com/facebook/react       →  facebook/react
#   https://github.com/facebook/react.git   →  facebook/react
#   https://github.com/facebook/react/      →  facebook/react
#   facebook/react                          →  facebook/react
def normalize_repo(text):
    s = text.strip()

    # 맨 뒤의 / 와 .git 을 떼어낸다. 순서가 중요하다.
    # ".git/" 처럼 둘 다 붙어 있을 수 있어서 / 를 먼저 뗀다.
    s = s.rstrip("/")
    if s.endswith(".git"):
        s = s[:-4]

    # 주소 형태로 넣었으면 앞의 https://github.com/ 부분을 잘라낸다.
    for prefix in ("https://", "http://"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    if s.startswith("www."):
        s = s[4:]
    if s.startswith("github.com/"):
        s = s[len("github.com/"):]

    # 남은 것에서 앞의 두 조각만 쓴다.
    # 뒤에 /tree/main 같은 게 붙어 있어도 여기서 잘린다.
    parts = s.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None

    return f"{parts[0]}/{parts[1]}"


# 저장소 이름을 파일 이름으로 바꾼다.
# facebook/react 의 / 는 경로 구분자라 그대로 쓰면 cache/facebook/react.json 이
# 되어버린다. facebook 폴더가 없다며 실패한다.
def cache_path(repo):
    return os.path.join(CACHE_DIR, repo.replace("/", "_") + ".json")


# 위 함수의 반대. 파일 이름에서 저장소 이름을 되돌린다.
# cache/ 를 훑는 stats.py, card.py, web.py 가 쓴다.
# GitHub 아이디에는 _ 가 들어갈 수 없어서, 첫 번째 _ 가 owner 와 repo 의 구분점이다.
#
#   octocat_Hello-World.json  ->  octocat/Hello-World
def repo_from_cache_name(name):
    return name[:-len(".json")].replace("_", "/", 1)


def save_cache(path, data):
    # 폴더가 없으면 그 안에 파일을 못 만든다. exist_ok=True 는 이미 있어도 넘어간다.
    os.makedirs(CACHE_DIR, exist_ok=True)

    # 한글 윈도우의 파이썬은 기본 인코딩이 cp949 다. utf-8 을 직접 지정하지 않으면 깨진다.
    # ensure_ascii=False 를 빼면 한글이 안녕 같은 코드로 저장돼 열어봐도 못 읽는다.
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_cache(path):
    # 저장할 때와 똑같이 utf-8 을 지정한다. 안 붙이면 읽을 때 깨진다.
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# GitHub 에서 참여자 통계를 받아온다. 받은 응답을 그대로 돌려준다.
# 상위 100명까지만 온다. 팀 저장소는 문제없지만 대형 저장소는 전원이 아니다.
def get_stats(repo, headers):
    url = f"{API}/repos/{repo}/stats/contributors"

    for i in range(1, RETRY_MAX + 1):
        res = requests.get(url, headers=headers)

        # 첫 호출은 202 와 빈 본문이 온다. GitHub 이 통계를 계산하는 중이라는 뜻이다.
        if res.status_code == 202:
            print(f"  {i}번째 시도: 202 (아직 계산 중) - {RETRY_WAIT}초 뒤에 다시 요청한다")
            time.sleep(RETRY_WAIT)
            continue

        # 권한이 없으면 GitHub 은 "없다" 고 답한다. 주소가 맞는데 404 면 비공개 저장소를 의심한다.
        if res.status_code == 404:
            print(f"  {repo} 를 찾을 수 없다. 주소가 맞다면 비공개 저장소일 수 있다.")
            return None

        # 요청 횟수를 다 쓰면 403 이나 429 가 온다.
        if res.status_code in (403, 429):
            remaining = res.headers.get("X-RateLimit-Remaining")
            print(f"  요청 횟수 제한에 걸렸다. (남은 횟수: {remaining})")
            return None

        # 커밋이 없는 새 저장소는 204 나 빈 본문을 준다.
        # 여기서 멈추지 않으면 아래 res.json() 이 터진다.
        if res.status_code == 204 or not res.content:
            print("  응답이 비어 있다. 커밋이 없는 저장소일 수 있다.")
            return None

        if res.status_code != 200:
            print(f"  예상 못한 응답: {res.status_code}")
            print(res.text)
            return None

        return res.json()

    print(f"  {RETRY_MAX}번 시도했는데 계속 202 다. 큰 저장소면 시간이 더 걸린다. 잠시 뒤 다시 실행한다.")
    return None


# GitHub 응답을 기획서가 정한 데이터 형태로 옮긴다.
# 키 이름을 바꾸지 않는다. 다른 파일이 이 이름으로 읽는다.
def to_our_form(raw):
    people = []

    for c in raw:
        # 커밋 이메일이 GitHub 계정과 연결돼 있지 않으면 author 가 None 으로 온다.
        # 그냥 두면 아래 c["author"]["login"] 이 TypeError 로 터진다.
        if c["author"] is None:
            continue

        # additions / deletions 는 합계 필드가 따로 없다. 주 단위 값을 직접 더해야 한다.
        additions = 0
        deletions = 0
        active_weeks = 0

        for w in c["weeks"]:
            additions += w["a"]
            deletions += w["d"]
            # 커밋이 한 번이라도 있는 주만 "활동한 주" 로 센다.
            if w["c"] > 0:
                active_weeks += 1

        # avatar_url 이 아니라 avatar 다. 그대로 쓰면 card.py 가 못 읽는다.
        people.append({
            "login": c["author"]["login"],
            "avatar": c["author"]["avatar_url"],
            "commits": c["total"],
            "additions": additions,
            "deletions": deletions,
            "active_weeks": active_weeks,
        })

    return people


# 이 파일의 입구. bot.py / web.py 도 이 함수를 부른다.
# 성공하면 딕셔너리 리스트를, 실패하면 None 을 돌려준다.
def get_contributors(repo_text):
    repo = normalize_repo(repo_text)
    if repo is None:
        print(f"저장소 주소를 알아볼 수 없다: {repo_text}")
        print("owner/repo 또는 https://github.com/owner/repo 형태로 넣는다.")
        return None

    path = cache_path(repo)

    # 이미 받아둔 파일이 있으면 API 를 부르지 않는다.
    # 요청 횟수를 아끼고, 시연 때 와이파이가 끊겨도 돌아간다.
    # 새로 받고 싶으면 그 파일을 지우고 다시 실행한다.
    if os.path.exists(path):
        print(f"캐시를 읽는다: {path}")
        return load_cache(path)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN 이 없다. .env 에 적었는지, 이 폴더에서 실행했는지 확인한다.")
        return None

    # 토큰 없이 부르면 시간당 60회에서 막힌다. 붙이면 5000회다.
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    print(f"GitHub 에 요청한다: {repo}")
    raw = get_stats(repo, headers)
    if raw is None:
        return None

    people = to_our_form(raw)
    save_cache(path, people)
    print(f"저장했다: {path}")

    return people


# 아래는 터미널에서 이 파일을 직접 실행했을 때만 돈다.
# bot.py 가 import 할 때는 실행되지 않는다. 이 줄이 없으면 import 만 해도 여기가 돌아버린다.
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python fetch.py owner/repo")
        print("예)    python fetch.py facebook/react")
        sys.exit(1)

    people = get_contributors(sys.argv[1])
    if people is None:
        sys.exit(1)

    # 잘 들어갔는지 눈으로 확인한다.
    print(f"참여자 {len(people)}명")
    for p in people:
        print(f"  {p['login']:<20} 커밋 {p['commits']:>5}  +{p['additions']:<7} -{p['deletions']:<7} {p['active_weeks']}주")
