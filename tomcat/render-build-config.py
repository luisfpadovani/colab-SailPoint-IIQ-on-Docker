"""Render SSB property templates from a BuildKit-mounted .env (never print values)."""
import re
import sys
from pathlib import Path


def render(env_path, ssb):
    values = {}
    for line in Path(env_path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ValueError("Invalid environment line")
        # Match quoted Compose env values without expanding dollar expressions.
        if value[:1] in ("'", '"') and value[-1:] == value[:1]:
            value = value[1:-1]
        values[key.strip()] = value
    for name in ("docker.iiq.properties", "docker.target.properties"):
        path = Path(ssb) / name
        content = path.read_text()
        def replace(match):
            key = match.group(1)
            value = values.get(key, "")
            if not re.fullmatch(r"[0-9]+:ACP:[A-Za-z0-9+/=]+", value):
                raise ValueError(f"Set {key} to an IIQ encrypt result in .env")
            return value
        path.write_text(re.sub(r"@@([A-Z_]+)@@", replace, content))


if __name__ == "__main__":
    render(*sys.argv[1:])
