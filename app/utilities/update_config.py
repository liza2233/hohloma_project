import asyncio
import httpx
import os


def clean_config(text: str) -> str:
    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip().replace("\ufeff", "")

        if not line:
            continue

        if line.lstrip().startswith("#"):
            continue

        if not line.startswith(("vless://", "vmess://", "trojan://", "ss://")):
            continue
        else:
            line = line.split("#")[0]


        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


async def write_file_atomic(path: str, data: str):
    temp_path = path + ".tmp"

    def _write():
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(data)

        os.replace(temp_path, path)

    await asyncio.to_thread(_write)

async def update_config(config_path, config_url):
    while True:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(config_url)
                response.raise_for_status()

                cleaned_text = clean_config(response.text)

                await write_file_atomic(config_path, cleaned_text)

                print("config.txt обновлён")

        except Exception as e:
            print(f"Ошибка: {e}")

        await asyncio.sleep(60 * 60 * 12)