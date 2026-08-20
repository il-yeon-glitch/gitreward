# 디스코드 연결 확인용 스크립트.
# 봇이 서버에 붙는지, 슬래시 명령이 그 서버에 등록되는지 두 가지만 본다.
# 카드 생성 같은 진짜 기능은 여기 넣지 않는다. bot.py 가 할 일이다.

import os
import sys

import discord
from discord import app_commands
from dotenv import load_dotenv

# .env 에 적어둔 값을 환경변수로 불러온다.
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

# 값이 없으면 여기서 멈춘다.
# 없는 채로 접속을 시도하면 한참 뒤에 엉뚱한 에러가 나서 원인을 찾기 어렵다.
if not TOKEN:
    print("DISCORD_TOKEN 이 없다. .env 에 적었는지, 이 폴더에서 실행했는지 확인한다.")
    sys.exit(1)

if not GUILD_ID:
    print("DISCORD_GUILD_ID 가 없다. 디스코드에서 서버 이름 우클릭 > '서버 ID 복사'.")
    sys.exit(1)

# 봇이 디스코드에서 받아볼 정보의 범위(intents).
# 슬래시 명령만 쓸 거라 기본값이면 충분하다.
# message_content 같은 특권 권한은 개발자 포털에서 따로 켜야 하는데, 여기선 필요 없다.
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# 슬래시 명령을 모아두는 목록. 여기 등록한 뒤 sync 로 디스코드 서버에 올린다.
tree = app_commands.CommandTree(bot)

# 명령을 등록할 서버. 서버 정보를 받아오지 않고 ID만 감싼 가벼운 참조다.
GUILD = discord.Object(id=int(GUILD_ID.strip()))


# @ 로 시작하는 줄은 데코레이터다. "아래 함수를 이런 용도로 등록해 달라" 는 표시다.
# 이 줄은 ping 함수를 슬래시 명령 /ping 으로 만든다.
# guild=GUILD 를 주면 이 서버에만 등록된다. 전역 등록은 반영이 한 시간까지 걸린다.
@tree.command(name="ping", description="봇이 살아 있는지 확인한다", guild=GUILD)
async def ping(interaction):
    # 바로 답할 수 있는 짧은 명령이라 defer() 없이 곧장 응답한다.
    # 오래 걸리는 명령이었다면 3초 제한 때문에 defer() 를 먼저 불러야 한다.
    await interaction.response.send_message("pong")


# @bot.event 는 "접속이 끝나면 이 함수를 불러 달라" 는 뜻이다.
# async / await 는 비동기 문법이다. 기다리는 동안 봇이 다른 일도 할 수 있게 해준다.
@bot.event
async def on_ready():
    print()
    print(f"봇 이름: {bot.user}  (ID: {bot.user.id})")
    print(f"접속한 서버: {len(bot.guilds)}개")

    for g in bot.guilds:
        print(f"  - {g.name}  (ID: {g.id})")
    print()

    # 명령을 등록할 서버에 봇이 실제로 들어가 있는지 먼저 본다.
    # 안 들어가 있으면 아래 sync 가 권한 에러로 실패하는데, 그 에러만 봐서는
    # ID 가 틀린 건지 초대를 안 한 건지 구분이 안 된다.
    target = bot.get_guild(GUILD.id)
    if target is None:
        print(f"DISCORD_GUILD_ID({GUILD.id}) 서버에 봇이 안 들어가 있다.")
        print("위에 나온 서버 목록과 ID 를 비교해 본다. 목록이 0개면 초대부터 해야 한다.")
        await bot.close()
        return

    # 이 서버에만 슬래시 명령을 등록한다. 등록된 명령 목록이 돌아온다.
    print(f"[슬래시 명령 등록] {target.name}")
    synced = await tree.sync(guild=GUILD)
    print(f"  등록된 명령: {len(synced)}개")

    for cmd in synced:
        print(f"  - /{cmd.name}")

    print()
    print("디스코드 앱에서 이 서버 채팅창에 / 를 눌러 목록에 /ping 이 보이는지 확인한다.")
    print("안 보이면 Ctrl+R 로 앱을 새로고침한다.")
    print("확인이 끝나면 Ctrl+C 로 끈다.")


# 봇을 켠다. 이 줄에서 멈춘 채로 계속 돈다. Ctrl+C 로 꺼야 빠져나온다.
bot.run(TOKEN)
