# 팀원들이 git commit/push/pull을 메뉴 선택만으로 할 수 있게 돕는 스크립트.
# git 명령어를 대신 실행해줄 뿐, 결과(성공/실패 메시지)는 그대로 보여준다.
# 실행: python git-auto.py

import subprocess


def run_git(*args):
    # git 명령어를 실행하고 결과를 돌려준다
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8")


def print_output(result):
    # git이 낸 메시지를 그대로 보여준다 (에러가 나도 숨기지 않는다)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())


def ask_yes_no(question):
    answer = input(f"{question} 1(예) 2(아니요): ").strip()
    return answer == "1"


def commit_and_push():
    status = run_git("status", "--short")
    if not status.stdout.strip():
        print("변경된 파일이 없습니다.")
        return

    print("변경된 파일 목록:")
    print(status.stdout)

    message = input("커밋 메세지를 입력하세요: ").strip()
    if not message:
        print("커밋 메세지가 비어 있어 취소합니다.")
        return

    if not ask_yes_no("커밋하시겠습니까?"):
        print("취소했습니다.")
        return

    print_output(run_git("add", "-A"))
    commit_result = run_git("commit", "-m", message)
    print_output(commit_result)
    if commit_result.returncode != 0:
        return

    if ask_yes_no("이어서 푸쉬하시겠습니까?"):
        print_output(run_git("push"))


def push_only():
    # @{u} 는 "내 브랜치가 추적하는 원격 브랜치"를 뜻한다. 연결이 안 돼 있으면 에러가 난다.
    log = run_git("log", "@{u}..HEAD", "--oneline")
    if log.returncode != 0:
        print("원격 브랜치 정보를 확인할 수 없습니다. (origin과 연결이 안 되어 있을 수 있음)")
        print_output(log)
        return

    if not log.stdout.strip():
        print("푸쉬할 커밋이 없습니다.")
        return

    print("아직 푸쉬 안 된 커밋 목록:")
    print(log.stdout)

    if ask_yes_no("푸쉬 하시겠습니까?"):
        print_output(run_git("push"))


def pull_only():
    status = run_git("status", "--short")
    if status.stdout.strip():
        print("커밋 안 된 변경사항이 있습니다. 먼저 커밋하거나 정리한 뒤 pull 하세요.")
        print(status.stdout)
        return

    if ask_yes_no("가지고 오시겠습니까?"):
        print_output(run_git("pull"))


def show_commands():
    # git-auto.py 없이 터미널에 바로 칠 수 있는 명령어 안내
    print(
        "\n"
        "git-auto.py 없이 직접 입력할 때 쓰는 명령어입니다.\n"
        "\n"
        "[커밋]\n"
        "  git add -A\n"
        '  git commit -m "커밋 메세지"\n'
        "\n"
        "[푸쉬]\n"
        "  git push\n"
        "\n"
        "[풀]\n"
        "  git pull\n"
    )


def main():
    while True:
        print(
            "\n"
            "1. 커밋 및 푸쉬\n"
            "2. 푸쉬\n"
            "3. 풀\n"
            "4. 취소\n"
            "5. 명령어 안내\n"
        )
        choice = input("번호를 선택하세요: ").strip()

        if choice == "1":
            commit_and_push()
        elif choice == "2":
            push_only()
        elif choice == "3":
            pull_only()
        elif choice == "4":
            break
        elif choice == "5":
            show_commands()
        else:
            print("1~5 중에서 선택해주세요.")


if __name__ == "__main__":
    main()
