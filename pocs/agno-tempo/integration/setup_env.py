"""Create local configuration and generate missing service secrets."""
import argparse
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET_BYTES = {
    "OS_SECURITY_KEY": 32,
    "BACKSTAGE_DB_PASSWORD": 24,
    "LIBRECHAT_JWT_SECRET": 32,
    "LIBRECHAT_JWT_REFRESH_SECRET": 32,
    "LIBRECHAT_CREDS_KEY": 32,
    "LIBRECHAT_CREDS_IV": 16,
    "GRAFANA_ADMIN_PASSWORD": 32,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    path = args.env
    if not path.exists():
        path.write_text((ROOT / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    lines = path.read_text(encoding="utf-8").splitlines()
    found = set()
    for index, line in enumerate(lines):
        key, separator, value = line.partition("=")
        key = key.strip()
        if separator and key in SECRET_BYTES:
            found.add(key)
            if not value.strip() or value.strip() in ('""', "''"):
                lines[index] = f"{key}={secrets.token_hex(SECRET_BYTES[key])}"
    for key, size in SECRET_BYTES.items():
        if key not in found:
            lines.append(f"{key}={secrets.token_hex(size)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Local service secrets initialized in {path}. Fill OPENAI_API_KEY before running.")


if __name__ == "__main__":
    main()
