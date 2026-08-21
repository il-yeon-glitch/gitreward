# 디스코드 봇. /card 명령으로 카드를 채널에 보낸다.
# 카드를 만드는 일은 여기서 하지 않는다. fetch -> stats -> card 를 순서대로 부를 뿐이다.
#
#   python bot.py     (Ctrl+C 로 끈다)
#
# 봇 토큰은 동시에 한 명만 쓸 수 있다. 두 명이 같은 토큰으로 켜면
# 응답이 두 번 오거나 한쪽이 조용히 끊긴다. 봇이 이상하면 팀에 먼저 물어본다.

import os
import secrets
import sys
from io import BytesIO

import discord
from discord import app_commands
from dotenv import load_dotenv

import db
import fetch
from stats import calc_stats, calc_level, calc_growth_stats, calc_left_points
from card import draw_card, card_stats, remove_cards
from config import WEB_BASE_URL, OAUTH_STATE_EXPIRE_SECONDS, TEAM_REPO

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

if not TOKEN:
    print("DISCORD_TOKEN 이 없다. .env 에 적었는지, 이 폴더에서 실행했는지 확인한다.")
    sys.exit(1)

if not GUILD_ID:
    print("DISCORD_GUILD_ID 가 없다. 디스코드에서 서버 이름 우클릭 > '서버 ID 복사'.")
    sys.exit(1)

# 슬래시 명령만 쓰므로 기본 권한이면 충분하다.
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# 명령을 등록할 서버. ID 만 감싼 가벼운 참조다.
GUILD = discord.Object(id=int(GUILD_ID.strip()))


# describe 는 디스코드 앱에서 각 칸에 뜨는 설명이다.
# repo: str 처럼 타입을 적는 건 discord.py 규칙이다. 이걸 보고 입력 칸의 종류를 정한다.
@tree.command(name="card", description="깃허브 기여 기록을 카드로 만든다", guild=GUILD)
@app_commands.describe(repo="저장소 주소 (owner/repo)", login="GitHub 아이디")
async def card_command(interaction, repo: str, login: str):
    # 디스코드는 명령 응답이 3초를 넘기면 실패 처리한다.
    # 카드를 만드는 데 그보다 오래 걸리니 먼저 시간을 벌어둔다.
    await interaction.response.defer()

    # defer() 를 부른 뒤에는 interaction.response 를 다시 쓸 수 없다. 응답은 한 번뿐이다.
    # 여기서부터 답은 전부 followup.send() 로 보낸다.

    # 아래 세 줄은 requests 를 쓰기 때문에 도는 동안 봇 전체가 멈춰 선다.
    # 해커톤 규모에서는 이대로도 시연이 되지만, 그동안 다른 명령을 못 받는다는 걸 알고 있어야 한다.
    # 그래서 시연 전에 미리 fetch.py 를 돌려 cache/ 에 저장해 두는 게 중요하다.
    people = fetch.get_contributors(repo)
    if people is None:
        await interaction.followup.send(
            f"`{repo}` 를 가져오지 못했다. 주소가 맞는지, 비공개 저장소가 아닌지 확인한다."
        )
        return

    # GitHub 아이디는 대소문자를 구분하지 않는다. 소문자로 맞춰서 찾는다.
    person = None
    for p in people:
        if p["login"].lower() == login.lower():
            person = p
            break

    if person is None:
        # 누가 있는지 알려줘야 다시 칠 수 있다. 너무 길어지지 않게 앞의 10명만 보여준다.
        names = ", ".join(p["login"] for p in people[:10])
        await interaction.followup.send(
            f"`{repo}` 에서 `{login}` 을 찾을 수 없다.\n참여자: {names}"
        )
        return

    # 레벨은 기여 기록에서, 카드에 그릴 HP/ATK/DEF 는 레벨 + 배분 포인트에서 나온다.
    level = calc_level(calc_stats(person))
    stats = card_stats(person, level, fetch.normalize_repo(repo))
    image = draw_card(person, stats, level)

    # 파일로 저장하지 않고 메모리에 담아 보낸다.
    buf = BytesIO()
    image.save(buf, format="PNG")

    # seek(0) 을 빠뜨리면 빈 파일이 전송된다.
    # 다 쓰고 나면 읽는 위치가 끝에 가 있어서, 되감지 않으면 읽을 게 없다.
    buf.seek(0)

    # discord.File 은 한 번만 보낼 수 있다. 다시 보내려면 새로 만들어야 한다.
    await interaction.followup.send(
        content=f"**{person['login']}** · Lv.{level} · `{repo}`",
        file=discord.File(buf, filename=f"{person['login']}.png"),
    )


@tree.command(name="등록", description="깃허브 저장소를 새로 받아온다", guild=GUILD)
@app_commands.describe(repo="저장소 주소 (owner/repo)")
async def register_command(interaction, repo: str):
    # /card 와 같은 이유로 defer() 부터 부른다. get_contributors() 가 몇 초 걸릴 수 있다.
    await interaction.response.defer()

    people = fetch.get_contributors(repo)
    if people is None:
        await interaction.followup.send(
            f"`{repo}` 를 가져오지 못했다. 주소가 맞는지, 비공개 저장소가 아닌지 확인한다."
        )
        return

    # 입력한 형태(주소, .git 등)와 상관없이 정리된 이름으로 안내한다.
    normalized = fetch.normalize_repo(repo)

    await interaction.followup.send(
        f"등록 완료! `{normalized}` (참여자 {len(people)}명)\n"
        f"웹에서 보기: {WEB_BASE_URL}/project/{normalized}"
    )


@tree.command(name="목록", description="지금까지 등록된 저장소 목록을 보여준다", guild=GUILD)
async def list_command(interaction):
    await interaction.response.defer()

    if not os.path.exists(fetch.CACHE_DIR):
        await interaction.followup.send("등록된 저장소가 없다. `/등록` 으로 먼저 추가한다.")
        return

    # web.py 의 load_people() 과 같은 방식으로 cache/ 를 훑는다.
    names = [n for n in os.listdir(fetch.CACHE_DIR) if n.endswith(".json")]
    if not names:
        await interaction.followup.send("등록된 저장소가 없다. `/등록` 으로 먼저 추가한다.")
        return

    lines = []
    for name in sorted(names):
        repo = fetch.repo_from_cache_name(name)
        lines.append(f"`{repo}` — {WEB_BASE_URL}/project/{repo}")

    await interaction.followup.send("등록된 저장소:\n" + "\n".join(lines))


@tree.command(name="웹", description="웹 페이지 주소를 보여준다", guild=GUILD)
async def web_command(interaction):
    # 링크만 보내는 거라 오래 걸리지 않는다. defer() 없이 바로 답해도 3초를 안 넘긴다.
    await interaction.response.send_message(
        f"팀 페이지: {WEB_BASE_URL}/project/{TEAM_REPO}\n"
        f"전체 순위: {WEB_BASE_URL}/all"
    )


@tree.command(name="갱신", description="깃허브에서 기여 기록을 다시 받아온다", guild=GUILD)
@app_commands.describe(repo="저장소 주소 (owner/repo). 비우면 팀 저장소를 갱신한다")
async def refresh_command(interaction, repo: str = None):
    await interaction.response.defer()

    # 인자를 안 주면 팀 저장소를 본다. 제일 자주 갱신할 대상이기 때문이다.
    if repo is None:
        repo = TEAM_REPO

    normalized = fetch.normalize_repo(repo)
    if normalized is None:
        await interaction.followup.send(
            f"`{repo}` 는 저장소 주소로 알아볼 수 없다. owner/repo 형태로 넣는다."
        )
        return

    path = fetch.cache_path(normalized)

    # fetch.get_contributors() 는 캐시 파일이 있으면 GitHub 에 묻지 않고 그대로 돌려준다.
    # 그래서 새로 받으려면 그 파일을 먼저 치워야 한다.
    #
    # 다만 지우자마자 요청이 실패하면(요청 횟수 초과, 와이파이 끊김) 원래 기록까지 잃는다.
    # 그래서 옛 기록을 메모리에 들고 있다가, 실패하면 그대로 되돌려 놓는다.
    old = fetch.load_cache(path) if os.path.exists(path) else None
    if old is not None:
        os.remove(path)

    people = fetch.get_contributors(normalized)

    if people is None:
        if old is not None:
            fetch.save_cache(path, old)
            await interaction.followup.send(
                f"`{normalized}` 를 새로 받지 못했다. 원래 기록은 그대로 두었다."
            )
        else:
            await interaction.followup.send(
                f"`{normalized}` 를 가져오지 못했다. 주소가 맞는지, 비공개 저장소가 아닌지 확인한다."
            )
        return

    # 기여 기록이 바뀌면 레벨과 능력치도 바뀐다. 그런데 make_card() 는 이미 있는
    # 파일을 그대로 쓰기 때문에, 지워 주지 않으면 웹에 옛날 카드가 계속 보인다.
    # 이 저장소 것만 지운다. 전부 지우면 다른 저장소 아바타까지 다시 받느라 느려진다.
    remove_cards(normalized)

    # 얼마나 늘었는지 같이 보여준다. 갱신하는 이유가 그것이기 때문이다.
    lines = [f"갱신 완료! `{normalized}` (참여자 {len(people)}명)"]

    now_commits = sum(p["commits"] for p in people)
    if old is None:
        lines.append(f"커밋 {now_commits}")
    else:
        old_commits = sum(p["commits"] for p in old)
        grew = now_commits - old_commits
        if grew > 0:
            lines.append(f"커밋 {old_commits} → {now_commits} (+{grew})")
        else:
            lines.append(f"커밋 {now_commits} (지난번과 같다)")

    lines.append(f"웹에서 보기: {WEB_BASE_URL}/project/{normalized}")

    await interaction.followup.send("\n".join(lines))


@tree.command(name="연결", description="디스코드 계정과 GitHub 계정을 연결한다", guild=GUILD)
async def link_command(interaction):
    # 링크에 1회용 토큰(state)이 들어가는데, 채널에 공개로 남으면 남이 가로챌 수 있다.
    # ephemeral=True 로 나에게만 보이게 보낸다.
    await interaction.response.defer(ephemeral=True)

    state = secrets.token_urlsafe(16)
    db.create_pending_link(state, str(interaction.user.id))

    url = f"{WEB_BASE_URL}/login?state={state}"
    minutes = OAUTH_STATE_EXPIRE_SECONDS // 60
    await interaction.followup.send(
        f"아래 링크에서 GitHub 로그인을 하면 계정이 연결돼. {minutes}분 안에 눌러야 해.\n{url}",
        ephemeral=True,
    )


# /능력치 와 /스텟분배 가 똑같이 하는 준비 작업이다. 두 곳에 적지 않으려고 함수로 뺐다.
# 성공하면 (사람, 레벨, 쓴포인트, None) 을, 실패하면 (None, None, None, 안내문) 을 돌려준다.
def load_my_card(discord_id, repo):
    # 여기가 "카드 주인만 만질 수 있게" 하는 자리다.
    # 명령을 친 사람의 discord_id 로 GitHub 아이디를 찾는다.
    # 아이디를 인자로 받지 않으므로 남의 카드를 지정할 방법 자체가 없다.
    login = db.get_linked_login(discord_id)
    if login is None:
        return None, None, None, "먼저 `/연결` 로 GitHub 계정을 연결한다."

    people = fetch.get_contributors(repo)
    if people is None:
        return None, None, None, f"`{repo}` 를 가져오지 못했다. `/등록` 을 먼저 한다."

    for p in people:
        if p["login"].lower() == login.lower():
            level = calc_level(calc_stats(p))
            return p, level, db.get_points(discord_id, repo), None

    return None, None, None, f"`{repo}` 에 `{login}` 의 기여 기록이 없다."


# 능력치 세 줄을 같은 모양으로 찍는다. 두 명령이 같은 형식으로 보여줘야 해서 여기 모았다.
def format_stats(person, level, points):
    g = calc_growth_stats(level, points)
    return (
        f"**{person['login']}** · Lv.{level}\n"
        f"체력 {g['HP']}  공격력 {g['ATK']}  방어력 {g['DEF']}"
    )


@tree.command(name="능력치", description="내 능력치와 남은 포인트를 본다", guild=GUILD)
async def mystats_command(interaction):
    await interaction.response.defer()

    discord_id = str(interaction.user.id)
    person, level, points, error = load_my_card(discord_id, TEAM_REPO)
    if error:
        await interaction.followup.send(error)
        return

    left = calc_left_points(level, points)
    await interaction.followup.send(
        f"{format_stats(person, level, points)}\n"
        f"배분 가능 포인트: **{left}**"
    )


@tree.command(name="스텟분배", description="남은 포인트를 능력치에 나눠 준다", guild=GUILD)
@app_commands.describe(hp="체력에 줄 포인트", atk="공격력에 줄 포인트", defense="방어력에 줄 포인트")
# 세 인자에 기본값(= 0)을 주지 않는다. 기본값이 있으면 디스코드가 "선택 사항" 으로 보고
# 어느 칸을 채울지 목록에서 고르게 만든다. 기본값을 없애면 세 칸을 차례로 다 물어본다.
# 대신 안 올릴 능력치에도 0 을 적어야 한다.
async def spend_command(interaction, hp: int, atk: int, defense: int):
    await interaction.response.defer()

    discord_id = str(interaction.user.id)
    person, level, points, error = load_my_card(discord_id, TEAM_REPO)
    if error:
        await interaction.followup.send(error)
        return

    left = calc_left_points(level, points)
    want = hp + atk + defense

    # 저장하기 전에 전부 검사한다. 하나라도 걸리면 DB 는 그대로 둔다.
    if hp < 0 or atk < 0 or defense < 0:
        await interaction.followup.send("음수는 넣을 수 없다.")
        return

    if want == 0:
        await interaction.followup.send(
            f"나눠 줄 포인트를 적는다. 지금 쓸 수 있는 건 {left} 개다."
        )
        return

    if want > left:
        await interaction.followup.send(
            f"포인트가 모자란다. 남은 건 {left} 개인데 {want} 개를 쓰려고 했다."
        )
        return

    db.add_points(discord_id, TEAM_REPO, hp, atk, defense)

    # 능력치가 바뀌었으니 이 사람 카드도 다시 그려져야 한다. 한 장만 지운다.
    remove_cards(TEAM_REPO, person["login"])

    after = db.get_points(discord_id, TEAM_REPO)
    await interaction.followup.send(
        f"배분 완료!\n"
        f"{format_stats(person, level, after)}\n"
        f"남은 포인트: **{calc_left_points(level, after)}**"
    )


@tree.command(name="help", description="사용할 수 있는 명령어 목록을 보여준다", guild=GUILD)
async def help_command(interaction):
    await interaction.response.defer()

    # -- 디스코드 봇이 추가될 때마다 자동으로 이 부분을 채운다 --
    # 명령을 새로 추가해도 여기를 따로 고칠 필요가 없다. tree 에 등록된
    # 명령들의 name/description 을 그대로 읽어오기 때문이다 (description 은
    # 각 명령의 @tree.command(...) 에 이미 적혀 있다. 두 곳에 적지 않는다).
    commands = sorted(tree.get_commands(guild=GUILD), key=lambda c: c.name)
    lines = [f"/{cmd.name} - {cmd.description}" for cmd in commands]

    await interaction.followup.send("사용할 수 있는 명령어:\n" + "\n".join(lines))


@bot.event
async def on_ready():
    print()
    print(f"봇 이름: {bot.user}  (ID: {bot.user.id})")
    print(f"접속한 서버: {len(bot.guilds)}개")

    for g in bot.guilds:
        print(f"  - {g.name}  (ID: {g.id})")
    print()

    # 명령을 등록할 서버에 봇이 실제로 들어가 있는지 먼저 본다.
    target = bot.get_guild(GUILD.id)
    if target is None:
        print(f"DISCORD_GUILD_ID({GUILD.id}) 서버에 봇이 안 들어가 있다.")
        print("위 서버 목록과 ID 를 비교해 본다. 목록이 0개면 초대부터 해야 한다.")
        await bot.close()
        return

    # 이 서버에만 등록한다. 전역 등록은 반영이 한 시간까지 걸린다.
    print(f"[슬래시 명령 등록] {target.name}")
    synced = await tree.sync(guild=GUILD)
    print(f"  등록된 명령: {len(synced)}개")

    for cmd in synced:
        print(f"  - /{cmd.name}")

    print()
    print("디스코드에서 /card 저장소 아이디 형태로 실행한다.")
    print("  예) /card  repo: octocat/Hello-World  login: Spaceghost")
    print("명령이 목록에 안 보이면 Ctrl+R 로 앱을 새로고침한다. 끄려면 Ctrl+C.")


# 로그인(계정 연결) 테이블이 없으면 여기서 만든다. web.py 도 시작할 때 따로 부른다.
db.init_db()

# 봇을 켠다. 이 줄에서 멈춘 채로 계속 돈다.
# 끌 때 RuntimeError: Event loop is closed 가 뜨는 건 윈도우에서 나오는 무해한 메시지다.
bot.run(TOKEN)

