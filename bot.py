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
from stats import calc_stats, calc_level
from card import draw_card
from config import WEB_BASE_URL, OAUTH_STATE_EXPIRE_SECONDS

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

    stats = calc_stats(person)
    level = calc_level(stats)
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

