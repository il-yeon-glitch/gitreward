# bot.py

> 디스코드 봇. `/card` 명령으로 카드를 채널에 보낸다.

## 역할

| | |
|---|---|
| 입력 | 디스코드 슬래시 명령 `/card repo: owner/repo login: 아이디` |
| 출력 | 채널에 카드 이미지 전송 |
| 실행 | `python bot.py` (Ctrl+C 로 끈다) |

**카드를 만드는 일은 여기서 하지 않습니다.** `fetch → stats → card` 를 순서대로 부를 뿐입니다.

```
디스코드 명령
   → fetch.get_contributors(repo)   참여자 목록
   → 그 중에서 login 찾기
   → calc_stats() / calc_level()    능력치
   → draw_card()                    이미지
   → followup.send()                전송
```

## 실행 방법

```bash
python bot.py
```

**정상 출력:**

```
봇 이름: GitReward#1234  (ID: 1234567890)
접속한 서버: 1개
  - YDAA 해커톤  (ID: 9876543210)

[슬래시 명령 등록] YDAA 해커톤
  등록된 명령: 1개
  - /card
```

디스코드 앱에서:

```
/card  repo: octocat/Hello-World  login: Spaceghost
```

명령이 목록에 안 보이면 **Ctrl+R 로 앱을 새로고침**합니다.

> **봇 토큰은 동시에 한 명만 쓸 수 있습니다.** 두 명이 같은 토큰으로 켜면 응답이 두 번 오거나 한쪽이 조용히 끊깁니다. 봇이 이상하면 팀에 먼저 물어봅니다.

---

## 비동기(async / await) 짚고 가기

이 파일에만 나오는 문법입니다.

```python
async def card_command(interaction, repo: str, login: str):
    await interaction.response.defer()
```

- `async def` — "이 함수는 중간에 **기다릴 수 있다**" 는 표시
- `await` — "여기서 기다린다. 기다리는 동안 **다른 일을 해도 된다**"

봇은 여러 사람의 명령을 동시에 받아야 합니다. 한 명의 요청을 처리하느라 멈춰 있으면 나머지가 전부 대기합니다. `await` 는 "네트워크 응답을 기다리는 동안 다른 명령을 받아라" 라고 알려주는 표시입니다.

**주의 — 이 파일의 `requests` 호출은 `await` 를 못 씁니다.** 그래서 그 동안은 봇 전체가 실제로 멈춥니다. 아래 "알고 있어야 할 것" 참고.

## 데코레이터 짚고 가기

`@` 로 시작하는 줄입니다. **"아래 함수를 이런 용도로 등록해 달라"** 는 표시입니다.

```python
@tree.command(name="card", description="...", guild=GUILD)
@app_commands.describe(repo="저장소 주소 (owner/repo)", login="GitHub 아이디")
async def card_command(interaction, repo: str, login: str):
```

| 줄 | 하는 일 |
|---|---|
| `@tree.command` | 이 함수를 슬래시 명령 `/card` 로 만든다 |
| `@app_commands.describe` | 디스코드 앱에서 각 입력 칸에 뜨는 설명 |

**`repo: str` 처럼 타입을 적는 건 discord.py 규칙입니다.** 이걸 보고 입력 칸의 종류(글자/숫자/사용자 선택)를 정합니다. 빼면 명령 등록이 실패합니다.

---

## 코드 구조

### 시작 부분 — 값 검사

```python
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

if not TOKEN:
    print("DISCORD_TOKEN 이 없다. ...")
    sys.exit(1)
```

**없으면 여기서 멈춥니다.** 없는 채로 접속을 시도하면 한참 뒤에 엉뚱한 에러가 나서 원인을 찾기 어렵습니다.

> `.env` 파일을 직접 열어보지 않습니다. `os.getenv()` 로만 값을 가져옵니다.

### intents 와 GUILD

```python
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

GUILD = discord.Object(id=int(GUILD_ID.strip()))
```

- **intents** — 봇이 디스코드에서 받아볼 정보의 범위. 슬래시 명령만 쓰니 기본값이면 충분합니다. `message_content` 같은 특권 권한은 개발자 포털에서 따로 켜야 하는데 여기선 필요 없습니다.
- **`discord.Object`** — 서버 정보를 실제로 받아오지 않고 **ID 만 감싼 가벼운 참조**입니다.
- `.strip()` — `.env` 에서 읽은 값 뒤에 공백이나 줄바꿈이 붙어 있으면 `int()` 가 터집니다.

### `defer()` — 3초 제한

```python
await interaction.response.defer()
```

**디스코드는 명령 응답이 3초를 넘기면 실패 처리합니다.** GitHub API 호출 + 아바타 다운로드 + 이미지 생성은 그보다 오래 걸립니다.

`defer()` 는 **"생각 중" 표시를 띄우고 시간을 버는 것**입니다. 이걸 안 부르면 카드가 잘 만들어져도 디스코드 쪽에서 이미 실패로 처리한 뒤입니다.

**중요 — `defer()` 를 부른 뒤에는 `interaction.response` 를 다시 쓸 수 없습니다.** 응답은 한 번뿐입니다. 그 다음부터 답은 전부 `followup.send()` 로 보냅니다.

```
interaction.response.defer()        ← 한 번만. 시간 벌기
interaction.followup.send(...)      ← 이후 모든 답장
```

### 참여자 찾기

```python
person = None
for p in people:
    if p["login"].lower() == login.lower():
        person = p
        break
```

**GitHub 아이디는 대소문자를 구분하지 않습니다.** `Spaceghost` 와 `spaceghost` 는 같은 사람입니다. 양쪽을 소문자로 맞춰 비교합니다.

```python
if person is None:
    names = ", ".join(p["login"] for p in people[:10])
    await interaction.followup.send(f"... 참여자: {names}")
```

**못 찾았을 때 누가 있는지 알려줍니다.** 그래야 다시 칠 수 있습니다. 500명짜리 저장소도 있으니 앞의 10명만 보여줍니다.

### BytesIO 전송 — seek(0)

```python
buf = BytesIO()
image.save(buf, format="PNG")
buf.seek(0)          # ★ 이 줄이 없으면 빈 파일이 전송된다

await interaction.followup.send(
    content=f"**{person['login']}** · Lv.{level} · `{repo}`",
    file=discord.File(buf, filename=f"{person['login']}.png"),
)
```

**`seek(0)` 이 이 파일에서 제일 빠뜨리기 쉬운 줄입니다.**

`BytesIO` 는 "메모리 위의 파일" 입니다. 파일에는 **읽고 쓰는 위치**가 있는데, `save()` 로 다 쓰고 나면 그 위치가 **끝에 가 있습니다.** 되감지 않고 디스코드가 읽으면 읽을 게 없어서 **0바이트 파일**이 갑니다.

```
save() 직후:   [PNG 데이터 32204바이트]▲   ← 위치가 끝
                                       읽으면 0바이트

seek(0) 후:   ▲[PNG 데이터 32204바이트]   ← 위치가 처음
              읽으면 32204바이트
```

에러가 안 나고 **빈 파일이 조용히 전송되는 게 함정**입니다.

> **`discord.File` 은 한 번만 보낼 수 있습니다.** 같은 객체를 두 번 보내려면 새로 만들어야 합니다.

### `on_ready()` — 접속 후 등록

```python
@bot.event
async def on_ready():
```

`@bot.event` 는 **"접속이 끝나면 이 함수를 불러 달라"** 는 뜻입니다.

```python
target = bot.get_guild(GUILD.id)
if target is None:
    print(f"DISCORD_GUILD_ID({GUILD.id}) 서버에 봇이 안 들어가 있다.")
    await bot.close()
    return
```

**sync 하기 전에 봇이 그 서버에 실제로 들어가 있는지 먼저 봅니다.** 안 들어가 있으면 `sync` 가 권한 에러로 실패하는데, 그 에러만 봐서는 **ID 가 틀린 건지 초대를 안 한 건지 구분이 안 됩니다.**

```python
synced = await tree.sync(guild=GUILD)
```

**길드 한정 sync 입니다.** `guild=` 를 빼면 전역 등록이 되는데, 반영에 **최대 한 시간**까지 걸립니다. 개발 중에는 못 씁니다.

> `sync(guild=...)` 는 그 서버의 명령을 **통째로 갈아끼웁니다.** `check_discord.py` 를 켜면 `/ping` 만 남고, `bot.py` 를 켜면 `/card` 만 남습니다. 둘 다 필요하면 한 파일에 있어야 합니다.

---

## 알고 있어야 할 것

### requests 가 봇을 멈춘다

```python
people = fetch.get_contributors(repo)   # 이 줄이 도는 동안 봇 전체가 멈춘다
```

`requests` 는 비동기 라이브러리가 아닙니다. 응답을 기다리는 동안 **다른 명령을 못 받습니다.**

해커톤 규모에서는 이대로도 시연이 되지만, **시연 전에 미리 `python fetch.py` 를 돌려 `cache/` 에 저장해 두는 게 중요합니다.** 캐시가 있으면 GitHub 호출을 건너뛰어서 훨씬 빠릅니다.

### 끌 때 뜨는 에러

```
RuntimeError: Event loop is closed
```

Ctrl+C 로 끌 때 뜨는 **윈도우에서 나오는 무해한 메시지**입니다. 고칠 필요 없습니다.

### 봇 초대 링크

봇을 서버에 초대할 때 **`applications.commands` 권한**이 들어 있어야 슬래시 명령이 보입니다. `bot` 만 체크하면 봇은 들어오는데 명령이 안 뜹니다.

---

## 확인 순서

1. `python check_discord.py` 로 `/ping` 이 되는지 먼저 확인
2. `python fetch.py <저장소>` 로 캐시를 미리 만들어 둔다
3. `python bot.py` 실행
4. 디스코드에서 `/card` 실행
5. 카드 이미지가 **0바이트가 아닌지** 확인 (seek(0) 검증)
