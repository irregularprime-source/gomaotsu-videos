"""保存バッチで、対象外のファイルの公開と、コミット後の統合失敗を防ぐ。

- ステージ済み: 対象外のファイルが git commit に混ざって公開されてしまう。
- 未ステージ: 対象外の追跡ファイルに変更があると、コミット後の git pull --rebase が
  失敗し、コミット済み・未反映のまま止まる。
どちらもユーザーの作業中の変更なので、中断するだけでステージ状態や内容は変えない。
"""
import subprocess
import sys


ALLOWED_FILES = {
    b"docs/videos.json", b"docs/tags.json", b"data/channels.json",
    b"docs/index.html", b"docs/sitemap.xml",
}


def unexpected_files(*diff_args):
    """対象外の変更ファイル一覧。git が失敗したら None。"""
    result = subprocess.run(
        ["git", "diff", *diff_args, "--name-only", "--no-renames", "-z"],
        capture_output=True,
    )
    if result.returncode:
        return None
    return [name for name in result.stdout.split(b"\0") if name and name not in ALLOWED_FILES]


def print_names(names):
    for name in names:
        print("  " + ascii(name.decode("utf-8", errors="surrogateescape")), file=sys.stderr)


def main():
    staged = unexpected_files("--cached")
    unstaged = unexpected_files()
    if staged is None or unstaged is None:
        print("[中断] ステージ済み・変更中のファイルを確認できませんでした。", file=sys.stderr)
        return 1
    if staged:
        print("[中断] 保存対象外のステージ済みファイルがあります。", file=sys.stderr)
        print_names(staged)
        print("対象外のファイルを別途保存するか、ステージから外して再実行してください。", file=sys.stderr)
        return 1
    if unstaged:
        # 未追跡の新規ファイルは pull --rebase を妨げないので対象にしない（git diff に出ない）。
        print("[中断] 保存対象外のファイルに、まだコミットしていない変更があります。", file=sys.stderr)
        print_names(unstaged)
        print("このまま保存すると最新状態との統合（git pull --rebase）に失敗するため保存しません。", file=sys.stderr)
        print("その変更を先にコミットするか元に戻してから、再実行してください。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
