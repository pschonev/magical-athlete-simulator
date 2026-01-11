import subprocess
import tomllib


def get_version():
    with open("pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def run():
    version = get_version()
    print(f"📦 Handling Git operations for v{version}...")

    # 1. Commit
    msg = f"chore(release): prepare v{version}"
    subprocess.run(["git", "commit", "-m", msg], check=True)

    # 2. Tag
    # Note: We tag just the number '0.7.0' to match your previous pattern
    # If you prefer 'v0.7.0', change to f"v{version}"
    subprocess.run(["git", "tag", version], check=True)

    print(f"✅ Committed and tagged v{version}")


if __name__ == "__main__":
    run()
