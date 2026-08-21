# 로그인(디스코드 계정 ↔ GitHub 계정 연결) 정보를 담는 SQLite 파일.
# web.py 의 /login, /callback 과 bot.py 의 /연결 명령이 이 파일의 함수만 불러 쓴다.
#
# 커넥션을 계속 들고 있지 않고, 함수를 부를 때마다 새로 열고 닫는다.
# web.py(Flask)와 bot.py(디스코드 봇)는 서로 다른 프로세스로 따로 실행되는데,
# sqlite 파일은 커넥션을 오래 붙들지만 않으면 여러 프로세스가 같이 열어도 안전하다.

import sqlite3
import time

from config import DB_PATH, OAUTH_STATE_EXPIRE_SECONDS


# 처음 한 번 불러서 테이블을 만들어 둔다. 이미 있으면 아무 일도 안 한다.
# web.py, bot.py 둘 다 시작할 때 각자 부른다.
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS linked_accounts (
            discord_id   TEXT PRIMARY KEY,
            github_login TEXT NOT NULL,
            linked_at    INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_links (
            state      TEXT PRIMARY KEY,
            discord_id TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    # 각 능력치에 "지금까지 쓴" 포인트만 담는다.
    # 레벨·최종 능력치·남은 포인트는 저장하지 않는다. stats.py 가 그때그때 계산한다.
    #
    # discord_id 와 repo 를 묶어 열쇠로 쓴다. 같은 사람이 저장소마다
    # 다른 캐릭터를 갖게 될 수 있어서다. 지금은 TEAM_REPO 하나만 쓴다.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stat_points (
            discord_id TEXT NOT NULL,
            repo       TEXT NOT NULL,
            hp         INTEGER NOT NULL DEFAULT 0,
            atk        INTEGER NOT NULL DEFAULT 0,
            defense    INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (discord_id, repo)
        )
        """
    )
    conn.commit()
    conn.close()


# /연결 명령이 만든 1회용 토큰(state)을 저장한다.
# 이 state 를 아는 사람만 이 discord_id 로 계정을 연결할 수 있다.
def create_pending_link(state, discord_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO pending_links (state, discord_id, created_at) VALUES (?, ?, ?)",
        (state, discord_id, int(time.time())),
    )
    conn.commit()
    conn.close()


# state 로 pending_links 를 찾는다. GitHub 콜백에서 한 번만 쓰고 버리는 값이라
# 찾으면 바로 지운다(1회용). 없거나 OAUTH_STATE_EXPIRE_SECONDS 를 넘겼으면 None.
def pop_pending_link(state):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT discord_id, created_at FROM pending_links WHERE state = ?", (state,)
    ).fetchone()

    if row is not None:
        conn.execute("DELETE FROM pending_links WHERE state = ?", (state,))
        conn.commit()
    conn.close()

    if row is None:
        return None

    discord_id, created_at = row
    if time.time() - created_at > OAUTH_STATE_EXPIRE_SECONDS:
        return None

    return discord_id


# GitHub 로그인이 끝나면 여기서 연결을 확정한다.
# 같은 discord_id 로 다시 연결하면 이전 값을 덮어쓴다(INSERT OR REPLACE).
def link_account(discord_id, github_login):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO linked_accounts (discord_id, github_login, linked_at) "
        "VALUES (?, ?, ?)",
        (discord_id, github_login, int(time.time())),
    )
    conn.commit()
    conn.close()


# 이 디스코드 유저가 연결해 둔 GitHub 로그인을 돌려준다. 연결한 적 없으면 None.
# 나중에 스텟 배분 명령에서 "카드 주인이 맞는지" 확인할 때 이 함수를 그대로 쓴다.
def get_linked_login(discord_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT github_login FROM linked_accounts WHERE discord_id = ?", (discord_id,)
    ).fetchone()
    conn.close()

    return row[0] if row else None


# SQL 컬럼은 소문자(hp/atk/defense)인데 파이썬에서는 대문자로 다룬다.
# stats.py 의 calc_growth_stats() 가 대문자 키를 받기 때문이다.
# 이름을 바꾸는 자리를 이 함수 하나로 모아둔다.
def _to_points(row):
    # 아직 한 번도 배분하지 않은 사람은 행이 아예 없다. 0 세 개로 본다.
    if row is None:
        return {"HP": 0, "ATK": 0, "DEF": 0}

    return {"HP": row[0], "ATK": row[1], "DEF": row[2]}


# 이 디스코드 유저가 이 저장소에서 지금까지 쓴 포인트를 돌려준다.
def get_points(discord_id, repo):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT hp, atk, defense FROM stat_points WHERE discord_id = ? AND repo = ?",
        (discord_id, repo),
    ).fetchone()
    conn.close()

    return _to_points(row)


# 위 함수를 GitHub 아이디로 찾는 버전.
# card.py / web.py 는 discord_id 를 모르고 login 만 안다. 그래서 두 표를 이어서 찾는다.
# GitHub 아이디는 대소문자를 가리지 않으므로 양쪽 다 소문자로 맞춰 비교한다.
def get_points_by_login(github_login, repo):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        """
        SELECT p.hp, p.atk, p.defense
        FROM stat_points p
        JOIN linked_accounts a ON a.discord_id = p.discord_id
        WHERE lower(a.github_login) = lower(?) AND p.repo = ?
        """,
        (github_login, repo),
    ).fetchone()
    conn.close()

    return _to_points(row)


# 이번에 나눠 준 만큼 기존 값에 더한다. 덮어쓰지 않는다.
# 행이 없을 때와 있을 때를 따로 쓰지 않으려고 INSERT OR REPLACE 를 쓴다.
def add_points(discord_id, repo, hp, atk, defense):
    now = get_points(discord_id, repo)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO stat_points (discord_id, repo, hp, atk, defense) "
        "VALUES (?, ?, ?, ?, ?)",
        (discord_id, repo, now["HP"] + hp, now["ATK"] + atk, now["DEF"] + defense),
    )
    conn.commit()
    conn.close()
