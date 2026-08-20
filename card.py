# 능력치를 받아 RPG 카드 PNG 를 만든다.
# 색과 크기는 여기 적지 않는다. 전부 config.py 에서 가져다 쓴다.
#
#   python card.py                              # cache/ 안의 저장소 전부
#   python card.py il-yeon-glitch/askme-project # 한 저장소만

import os
import sys
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

from config import (
    STAT_NAMES,
    CARD_WIDTH, CARD_HEIGHT, CARD_PADDING,
    CARD_BG, CARD_ACCENT, CARD_TEXT, CARD_SUB, CARD_BAR_BG,
    FONT_PATH, FONT_SIZE_NAME, FONT_SIZE_LEVEL, FONT_SIZE_STAT,
    AVATAR_SIZE, AVATAR_TOP, NAME_TOP, LEVEL_TOP,
    STAT_TOP, STAT_ROW_HEIGHT, BAR_HEIGHT, BAR_MAX,
    CARD_DIR,
)
from fetch import CACHE_DIR, load_cache, normalize_repo, cache_path, repo_from_cache_name
from stats import calc_stats, calc_level


# 프로필 이미지를 받아 카드에 넣을 크기로 줄인다.
def load_avatar(url):
    res = requests.get(url)
    img = Image.open(BytesIO(res.content)).convert("RGB")
    return img.resize((AVATAR_SIZE, AVATAR_SIZE))


# 정사각형 이미지를 원형으로 보이게 하는 마스크를 만든다.
# 마스크는 흑백 이미지다. 흰(255) 부분만 붙고 검은(0) 부분은 안 붙는다.
# 이미지 자체를 자르는 게 아니라, 붙일 때 어디를 붙일지 알려주는 방식이다.
def make_circle_mask(size):
    mask = Image.new("L", (size, size), 0)
    # ellipse 는 사각형 안에 꽉 찬 타원을 그린다. 정사각형이면 원이 된다.
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask


# 카드 한 장을 그려서 이미지를 돌려준다. 파일로 저장하지는 않는다.
# person 은 fetch.py 가 만든 딕셔너리, stats 와 level 은 stats.py 가 만든 값이다.
# bot.py 는 파일을 만들지 않고 메모리로 바로 보내야 해서 이 함수를 쓴다.
def draw_card(person, stats, level):
    card = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), CARD_BG)
    draw = ImageDraw.Draw(card)

    # 폰트는 크기별로 따로 불러와야 한다. 한 번 만든 폰트의 크기는 못 바꾼다.
    font_name = ImageFont.truetype(FONT_PATH, FONT_SIZE_NAME)
    font_level = ImageFont.truetype(FONT_PATH, FONT_SIZE_LEVEL)
    font_stat = ImageFont.truetype(FONT_PATH, FONT_SIZE_STAT)

    # --- 프로필 이미지 (원형) ---
    try:
        avatar = load_avatar(person["avatar"])
    except Exception as e:
        # 시연 중에 와이파이가 끊겨도 카드는 나오게 한다. 원인은 화면에 남긴다.
        print(f"  아바타를 못 받았다: {e}")
        avatar = Image.new("RGB", (AVATAR_SIZE, AVATAR_SIZE), CARD_BAR_BG)

    avatar_x = (CARD_WIDTH - AVATAR_SIZE) // 2
    card.paste(avatar, (avatar_x, AVATAR_TOP), make_circle_mask(AVATAR_SIZE))

    # --- 이름과 레벨 ---
    # anchor="mm" 은 "이 좌표가 글자의 한가운데" 라는 뜻이다.
    # 글자 폭을 재서 직접 가운데를 맞출 필요가 없어진다.
    draw.text((CARD_WIDTH // 2, NAME_TOP), person["login"],
              font=font_name, fill=CARD_TEXT, anchor="mm")
    draw.text((CARD_WIDTH // 2, LEVEL_TOP), f"Lv. {level}",
              font=font_level, fill=CARD_ACCENT, anchor="mm")

    # --- 능력치 막대 ---
    bar_width = CARD_WIDTH - CARD_PADDING * 2
    y = STAT_TOP

    for key in STAT_NAMES:
        value = stats[key]

        # 능력치 이름은 왼쪽, 값은 오른쪽에 붙인다.
        draw.text((CARD_PADDING, y), STAT_NAMES[key],
                  font=font_stat, fill=CARD_SUB, anchor="lm")
        draw.text((CARD_WIDTH - CARD_PADDING, y), str(value),
                  font=font_stat, fill=CARD_TEXT, anchor="rm")

        # 막대는 두 번 그린다. 빈 막대를 먼저 깔고, 그 위에 값만큼 덮는다.
        bar_y = y + 25
        draw.rectangle(
            [CARD_PADDING, bar_y, CARD_PADDING + bar_width, bar_y + BAR_HEIGHT],
            fill=CARD_BAR_BG,
        )

        # BAR_MAX 를 넘으면 꽉 찬 막대로 자른다.
        ratio = min(value / BAR_MAX, 1.0)
        if ratio > 0:
            draw.rectangle(
                [CARD_PADDING, bar_y, CARD_PADDING + int(bar_width * ratio), bar_y + BAR_HEIGHT],
                fill=CARD_ACCENT,
            )

        y += STAT_ROW_HEIGHT

    return card


# 카드를 그려서 static/ 에 저장하고, 저장한 경로를 돌려준다.
# 터미널에서 눈으로 확인할 때와 web.py 가 쓴다.
def make_card(person, stats, level, repo):
    # 폴더가 없으면 파일을 못 만든다.
    os.makedirs(CARD_DIR, exist_ok=True)

    # 파일 이름에 저장소를 넣는다. 아이디만 쓰면 같은 사람이 여러 저장소에 있을 때
    # 나중에 만든 카드가 앞의 것을 덮어써서, 한 명당 한 장만 남는다.
    name = f"{repo.replace('/', '_')}_{person['login']}.png"
    path = os.path.join(CARD_DIR, name)

    # 이미 만든 카드가 있으면 다시 그리지 않는다. draw_card() 가 아바타를
    # GitHub 에서 매번 새로 받아오기 때문에, 저장소가 몇 개만 쌓여도
    # web.py 가 새로고침될 때마다 수십~수백 번 요청을 보내 느려진다.
    # config.py 값을 바꾸고 바로 확인하고 싶으면 static/ 을 지우고 새로고침한다.
    if os.path.exists(path):
        return path

    card = draw_card(person, stats, level)
    card.save(path)

    return path


# 아래는 터미널에서 직접 실행했을 때만 돈다.
if __name__ == "__main__":
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

    made = 0
    for name in names:
        path = os.path.join(CACHE_DIR, name)
        if not os.path.exists(path):
            print(f"{path} 가 없다. 먼저 python fetch.py 로 받는다.")
            continue

        # 파일 이름에서 저장소 이름을 되돌린다. 카드 파일명에 넣어야 한다.
        repo = repo_from_cache_name(name)

        print(f"=== {name} ===")
        for person in load_cache(path):
            stats = calc_stats(person)
            level = calc_level(stats)
            out = make_card(person, stats, level, repo)
            print(f"  {out}  (Lv.{level}  {stats})")
            made += 1

    print()
    print(f"카드 {made}장을 {CARD_DIR}/ 에 만들었다.")
