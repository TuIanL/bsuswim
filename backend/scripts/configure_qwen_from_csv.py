"""Configure the ignored backend .env from a DashScope/Qwen API-key export.

The script intentionally never prints the key. It is for local deployment only
and must not be committed with the generated .env file.
"""

import argparse
import csv
import json
from pathlib import Path


def _replace_env(lines: list[str], values: dict[str, str]) -> list[str]:
    remaining = dict(values)
    output: list[str] = []
    for line in lines:
        name = line.split("=", 1)[0].strip() if "=" in line else ""
        if name in remaining:
            output.append(f"{name}={json.dumps(remaining.pop(name), ensure_ascii=False)}\n")
        else:
            output.append(line if line.endswith("\n") else f"{line}\n")
    if remaining:
        output.append("\n# Qwen report interpretation\n")
        output.extend(f"{name}={json.dumps(value, ensure_ascii=False)}\n" for name, value in remaining.items())
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--model", default="qwen-plus")
    args = parser.parse_args()

    with args.csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if rows and set(rows[0]).issuperset({"apiKey", "apiHost"}):
        fields = rows[0]
        values_row = rows[1] if len(rows) > 1 else []
        row = dict(zip(fields, values_row))
    else:
        # Alibaba Cloud console exports this API key page as two-column
        # key/value rows rather than a conventional header table.
        row = {item[0]: item[1] for item in rows if len(item) >= 2}
    if not row.get("apiKey") or not row.get("apiHost"):
        raise SystemExit("CSV 缺少 apiKey 或 apiHost")
    host = str(row.get("openAiCompatible") or row["apiHost"]).rstrip("/")
    if not host.startswith("https://"):
        raise SystemExit("apiHost 必须使用 HTTPS")

    values = {
        "AI_INTERPRETATION_ENABLED": "true",
        "AI_INTERPRETATION_AUTO_GENERATE": "false",
        "AI_INTERPRETATION_PROVIDER": "qwen",
        "AI_INTERPRETATION_BASE_URL": host,
        "AI_INTERPRETATION_MODEL": args.model,
        "AI_INTERPRETATION_API_KEY": str(row["apiKey"]),
        "AI_INTERPRETATION_VISUAL_ENABLED": "false",
        "AI_INTERPRETATION_MODEL_SUPPORTS_VISION": "false",
        "AI_INTERPRETATION_MODEL_SUPPORTS_STRUCTURED_OUTPUT": "true",
    }
    original = args.env.read_text(encoding="utf-8").splitlines(keepends=True) if args.env.exists() else []
    args.env.write_text("".join(_replace_env(original, values)), encoding="utf-8")
    print(f"已配置 Qwen provider: host={host}, model={args.model}, visual_mode=false")


if __name__ == "__main__":
    main()
