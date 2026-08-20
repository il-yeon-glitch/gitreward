# check_discord.py

> 디스코드 연결 확인용. **본 기능이 아니라 준비 단계 스크립트다.**

## 역할

| | |
|---|---|
| 입력 | 없음 (`.env` 의 토큰과 서버 ID) |
| 출력 | 콘솔에 봇 이름·서버 목록, 디스코드에 `/ping` 명령 등록 |
| 실행 | `python check_discord.py` (Ctrl+C 로 끈다) |

두 가지만 봅니다.

1. **봇이 서버에 붙나**
2. **슬래시 명령이 그 서버에 등록되나**

**카드 생성 같은 진짜 기능은 여기 넣지 않습니다.** `bot.py` 가 할 일입니다.

> `bot.py` 의 뼈대와 거의 같습니다. 다른 건 명령이 `/card` 대신 `/ping` 이라는 것뿐입니다. **디스코드 쪽 연결만 따로 떼어내 확인**하는 게 목적입니다. `/card` 가 안 될 때 "디스코드 문제인지 GitHub 문제인지" 를 가르는 기준선이 됩니다.

## 실행 방법

```bash
python check_discord.py
```

**정상 출력:**

```
봇 이름: GitReward#1234  (ID: 1234567890123)
접속한 서버: 1개
  - YDAA 해커톤  (ID: 9876543210987)

[슬래시 명령 등록] YDAA 해커톤
  등록된 명령: 1개
  - /ping

디스코드 앱에서 이 서버 채팅창에 / 를 눌러 목록에 /ping 이 보이는지 확인한다.
```

**콘솔 출력만으로는 절반입니다.** 디스코드 앱에서 직접 확인해야 합니다.

1. 그 서버의 아무 채널에서 `/` 를 친다
2. 목록에 `/ping` 이 보인다
3. 실행하면 `pong` 이 온다

**"보이는 것" 과 "응답하는 것" 은 다릅니다.** 명령이 목록에 보여도 봇이 꺼져 있으면 "애플리케이션이 응답하지 않습니다" 가 뜹니다. 명령 등록은 디스코드 서버에 남고, 응답은 켜져 있는 봇이 하기 때문입니다.

명령이 안 보이면 **Ctrl+R 로 앱을 새로고침**합니다.

---

## 코드 구조

### 시작 부분 — 값 검사

```python
if not TOKEN:
    print("DISCORD_TOKEN 이 없다. .env 에 적었는지, 이 폴더에서 실행했는지 확인한다.")
    sys.exit(1)

if not GUILD_ID:
    print("DISCORD_GUILD_ID 가 없다. 디스코드에서 서버 이름 우클릭 > '서버 ID 복사'.")
    sys.exit(1)
```

**없으면 여기서 멈춥니다.** 없는 채로 접속을 시도하면 한참 뒤에 엉뚱한 에러가 나서 원인을 찾기 어렵습니다.

> **서버 ID 를 복사하려면** 디스코드 설정 > 고급 > **개발자 모드**를 켜야 우클릭 메뉴에 나옵니다.
> 서버 ID 는 비밀이 아니라 공유해도 되지만, **토큰은 절대 카톡·디스코드로 주고받지 않습니다.** 채팅 기록에 남습니다.

### intents

```python
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
```

**intents 는 봇이 디스코드에서 받아볼 정보의 범위**입니다. 슬래시 명령만 쓸 거라 기본값이면 충분합니다.

`message_content`(남의 메시지 내용 읽기) 같은 **특권 권한**은 개발자 포털에서 따로 켜야 하는데, 여기선 필요 없습니다. 안 쓰는 권한을 켜면 봇 심사가 까다로워지기만 합니다.

> `discord.Client` 를 쓴 이유 — `commands.Bot` 을 쓰면 `command_prefix="!"` 를 억지로 넣어야 하고(우린 `!명령` 을 안 씁니다), 슬래시 명령만 쓰는데도 **"message content intent 가 없다" 는 오해를 부르는 경고**가 뜹니다.

### CommandTree 와 GUILD

```python
tree = app_commands.CommandTree(bot)
GUILD = discord.Object(id=int(GUILD_ID.strip()))
```

- **`CommandTree`** — 슬래시 명령을 모아두는 목록. 여기 등록한 뒤 `sync` 로 디스코드 서버에 올립니다.
- **`discord.Object`** — 서버 정보를 실제로 받아오지 않고 **ID 만 감싼 가벼운 참조**입니다.
- `.strip()` — `.env` 에서 읽은 값 뒤에 공백이나 줄바꿈이 붙어 있으면 `int()` 가 터집니다.

### `/ping` 명령

```python
@tree.command(name="ping", description="봇이 살아 있는지 확인한다", guild=GUILD)
async def ping(interaction):
    await interaction.response.send_message("pong")
```

**`@` 로 시작하는 줄은 데코레이터**입니다. "아래 함수를 이런 용도로 등록해 달라" 는 표시입니다. 이 줄이 `ping` 함수를 슬래시 명령 `/ping` 으로 만듭니다.

**`guild=GUILD` 를 주면 이 서버에만 등록됩니다.** 빼면 전역 등록인데 반영에 **최대 한 시간**까지 걸려서 개발 중에는 못 씁니다.

```python
await interaction.response.send_message("pong")
```

**여기는 `defer()` 를 안 씁니다.** 바로 답할 수 있는 짧은 명령이기 때문입니다. `bot.py` 의 `/card` 는 카드를 만드느라 3초를 넘겨서 `defer()` 를 먼저 불러야 합니다.

> **`async` / `await` 는 비동기 문법**입니다. `await` 는 "여기서 기다린다, 기다리는 동안 봇이 다른 일을 해도 된다" 는 표시입니다. 봇은 여러 사람의 명령을 동시에 받아야 해서 이 방식을 씁니다.

### `on_ready()` — 접속 후

```python
@bot.event
async def on_ready():
```

`@bot.event` 는 **"접속이 끝나면 이 함수를 불러 달라"** 는 뜻입니다. 접속에 몇 초가 걸리므로, 코드 아래쪽에 그냥 적으면 아직 접속 전이라 봇 정보가 없습니다.

```python
target = bot.get_guild(GUILD.id)
if target is None:
    print(f"DISCORD_GUILD_ID({GUILD.id}) 서버에 봇이 안 들어가 있다.")
    print("위에 나온 서버 목록과 ID 를 비교해 본다. 목록이 0개면 초대부터 해야 한다.")
    await bot.close()
    return
```

**sync 전에 봇이 그 서버에 실제로 들어가 있는지 먼저 봅니다.**

안 들어가 있으면 `sync` 가 권한 에러로 실패하는데, **그 에러만 봐서는 ID 가 틀린 건지 초대를 안 한 건지 구분이 안 됩니다.** 서버 목록을 위에 미리 찍어두고 ID 를 비교하게 만든 이유입니다.

```python
synced = await tree.sync(guild=GUILD)
for cmd in synced:
    print(f"  - /{cmd.name}")
```

`sync` 는 **등록된 명령 목록을 돌려줍니다.** 이걸 찍어서 "정말 올라갔는지" 를 콘솔에서 먼저 확인합니다.

### `bot.run(TOKEN)`

**이 줄에서 멈춘 채로 계속 돕니다.** Ctrl+C 로 꺼야 빠져나옵니다. 터미널이 안 돌아온다고 멈춘 게 아닙니다 — 원래 그렇습니다.

---

## 알고 있어야 할 것

### sync 는 통째로 갈아끼운다

`tree.sync(guild=...)` 는 그 서버의 명령을 **전부 교체**합니다.

```
check_discord.py 를 켜면  →  그 서버에 /ping 만 남는다
bot.py 를 켜면            →  그 서버에 /card 만 남는다
```

`/card` 를 쓰다가 `check_discord.py` 를 켜면 `/card` 가 사라집니다. 놀라지 말고 `bot.py` 를 다시 켜면 됩니다.

### 봇 초대 링크

봇을 서버에 초대할 때 **`applications.commands` 권한**이 들어 있어야 슬래시 명령이 보입니다. `bot` 만 체크하면 봇은 들어오는데 명령이 안 뜹니다.

### 토큰은 한 명만

**봇 토큰은 동시에 한 사람만 쓸 수 있습니다.** 두 명이 같은 토큰으로 켜면 응답이 두 번 오거나 한쪽이 조용히 끊깁니다. 봇이 이상하면 팀에 먼저 물어봅니다.

### 끌 때 뜨는 에러

```
RuntimeError: Event loop is closed
```

Ctrl+C 로 끌 때 나오는 **윈도우에서 나오는 무해한 메시지**입니다. 고칠 필요 없습니다.

---

## 문제가 생겼을 때

| 증상 | 원인 |
|---|---|
| `접속한 서버: 0개` | 봇을 서버에 초대하지 않았다 |
| `DISCORD_GUILD_ID ... 서버에 봇이 안 들어가 있다` | ID 가 틀렸거나 다른 서버 ID |
| 콘솔은 정상인데 앱에 `/ping` 이 안 보인다 | Ctrl+R 로 새로고침 / 초대 링크에 `applications.commands` 누락 |
| `애플리케이션이 응답하지 않습니다` | 봇이 꺼져 있다 (명령 등록은 남아 있음) |
| `improper token` | 토큰이 틀렸다. 개발자 포털에서 재발급 |
