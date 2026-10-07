"""保存バッチで対象外のステージ済みファイルが公開されることを防ぐ。"""
import subprocess
import sys


ALLOWED_FILES = {
    b"docs/videos.json", b"docs/tags.json", b"data/channels.json",
    b"docs/index.html", b"docs/sitemap.xml",
}


def main():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--no-renames", "-z"],
        capture_output=True,
    )
    if result.returncode:
        print("[中断] ステージ済みファイルを確認できませんでした。", file=sys.stderr)
        return 1
    unexpected = [name for name in result.stdout.split(b"\0") if name and name not in ALLOWED_FILES]
    if unexpected:
        print("[中断] 保存対象外のステージ済みファイルがあります。", file=sys.stderr)
        for name in unexpected:
            print("  " + ascii(name.decode("utf-8", errors="surrogateescape")), file=sys.stderr)
        print("対象外のファイルを別途保存するか、ステージから外して再実行してください。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
