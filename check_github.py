# GitHub 연결 확인용 스크립트.
# 토큰이 살아 있는지, 참여자 통계를 받아올 수 있는지 두 가지만 본다.
# 받은 응답에서 값을 꺼내지 않는다. 구조를 눈으로 보는 게 목적이다.

import os
import sys
import json
import time

import requests
from dotenv import load_dotenv

# .env 에 적어둔 값을 환경변수로 불러온다.
# 이 줄을 빠뜨리면 아래 os.getenv 가 계속 None 을 돌려준다.
load_dotenv()

API = "https://api.github.com"

# 저장소를 안 적고 실행했을 때 쓸 기본값.
# 응답이 짧아야 눈으로 읽을 수 있으므로 아주 작은 저장소로 둔다.
DEFAULT_REPO = "octocat/Hello-World"

# 202(아직 계산 중) 가 오면 잠깐 쉬었다가 다시 물어본다.
RETRY_MAX = 5
RETRY_WAIT = 2


# 요청에 붙일 헤더를 만든다. 토큰이 없으면 None 을 돌려준다.
def make_headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None

    # 토큰 값 자체는 어디에도 출력하지 않는다.
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


# 1단계 - 토큰이 살아 있는지 확인한다.
# /user 는 "이 토큰의 주인이 누구냐" 를 묻는 주소다. 권한을 안 줘도 답해준다.
def check_token(headers):
    print("[1단계] 토큰 확인")
    print(f"  GET {API}/user")

    res = requests.get(f"{API}/user", headers=headers)
    print(f"  응답 코드: {res.status_code}")

    if res.status_code == 200:
        print(f"  토큰 주인: {res.json()['login']}")
    elif res.status_code == 401:
        print("  토큰이 잘못됐거나 만료됐다. .env 의 GITHUB_TOKEN 을 다시 확인한다.")
    else:
        print("  예상 못한 응답이다. 본문을 그대로 보여준다.")
        print(res.text)

    # 남은 요청 횟수. 토큰이 제대로 붙었으면 5000, 안 붙었으면 60 이다.
    remaining = res.headers.get("X-RateLimit-Remaining")
    limit = res.headers.get("X-RateLimit-Limit")
    print(f"  남은 요청 횟수: {remaining} / {limit}  (5000 이면 토큰이 붙은 것, 60 이면 안 붙은 것)")
    print()

    return res.status_code == 200


# 2단계 - 참여자 통계를 요청한다.
# 이 주소는 첫 호출에서 202 와 빈 본문을 준다. GitHub 이 통계를 계산하는 중이라는 뜻이다.
def get_contributor_stats(repo, headers):
    url = f"{API}/repos/{repo}/stats/contributors"

    print("[2단계] 참여자 통계 요청")
    print(f"  GET {url}")

    for i in range(1, RETRY_MAX + 1):
        res = requests.get(url, headers=headers)
        size = len(res.content)
        print(f"  {i}번째 시도 -> {res.status_code} (본문 {size}바이트)")

        # ★ 여기가 알려진 함정이다. 본문이 비어 있으니 그대로 쓰면 안 된다.
        if res.status_code == 202:
            print(f"     202: 아직 계산 중이고 본문이 비어 있다. {RETRY_WAIT}초 기다렸다 다시 물어본다.")
            time.sleep(RETRY_WAIT)
            continue

        # 커밋이 없는 새 저장소는 204 나 빈 본문이 올 수 있다.
        if size == 0:
            print("     본문이 비어 있다. 커밋이 없는 저장소일 수 있다.")
            return None

        return res

    print(f"  {RETRY_MAX}번 시도했는데 계속 202 다. 큰 저장소면 시간이 더 걸린다. 잠시 뒤 다시 실행한다.")
    return None


# 3단계 - 받은 응답을 보여준다.
# 값을 꺼내거나 키 이름을 바꾸지 않는다. 줄바꿈과 들여쓰기만 넣는다.
def print_response(res):
    print()
    print("[3단계] 받은 응답")
    print(f"  응답 코드: {res.status_code}")
    print(f"  크기: {len(res.content)}바이트")
    print("-" * 60)

    print(json.dumps(res.json(), indent=2, ensure_ascii=False))


# 여기서부터 실제로 실행된다.

# 실행할 때 뒤에 저장소를 적으면 그걸 쓰고, 안 적으면 기본값을 쓴다.
if len(sys.argv) > 1:
    repo = sys.argv[1]
else:
    repo = DEFAULT_REPO

print(f"확인할 저장소: {repo}")
print()

headers = make_headers()
if headers is None:
    print("GITHUB_TOKEN 이 없다.")
    print(".env 파일에 GITHUB_TOKEN=... 을 적었는지, 이 폴더에서 실행했는지 확인한다.")
    sys.exit(1)

if not check_token(headers):
    sys.exit(1)

res = get_contributor_stats(repo, headers)
if res is None:
    sys.exit(1)

print_response(res)
