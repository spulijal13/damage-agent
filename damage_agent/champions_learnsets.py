"""Local Champions learnsets, refreshed only by an explicit administrator action."""
import json
import os
import tempfile
import re
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = 'https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/champions/learnsets.ts'
FALLBACK_PATH = Path(__file__).resolve().parents[1] / 'data/champions_learnsets.json'


def parse_learnsets(text):
    # Parse only the data-shaped learnset blocks; never execute downloaded code.
    entries = re.findall(r'^\t([a-z0-9]+): \{\n(.*?)^\t\},', text, re.M | re.S)
    result = {}
    for name, body in entries:
        block = re.search(r'\t\tlearnset: \{\n(.*?)\n\t\t\}', body, re.S)
        if not block:
            raise ValueError('Unexpected Showdown learnset format.')
        result[name] = re.findall(r'^\t\t\t([a-z0-9]+): \[', block[1], re.M)
    if len(result) < 200 or not result.get('venusaur'):
        raise ValueError('Incomplete Showdown learnset response.')
    return result


def get_learnsets():
    return {'learnsets': json.loads(FALLBACK_PATH.read_text(encoding='utf-8')),
            'source': 'local', 'url': SOURCE_URL}


def refresh_learnsets():
    """Explicit refresh for the CLI and a future authenticated admin action.

    Failed downloads or validation leave the existing file untouched. Atomic
    replacement ensures readers never observe a partially written JSON file.
    """
    request = Request(SOURCE_URL, headers={'User-Agent': 'DamageAgent/1.0'})
    with urlopen(request, timeout=30) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError('Showdown learnset response exceeds the size limit.')
    data = parse_learnsets(payload.decode('utf-8'))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=FALLBACK_PATH.parent, suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            json.dump(data, output, indent=2, ensure_ascii=False)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, FALLBACK_PATH.stat().st_mode & 0o777)
        os.replace(temporary, FALLBACK_PATH)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return len(data)


if __name__ == '__main__':
    try:
        count = refresh_learnsets()
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Refresh failed; existing learnsets preserved: {exc}') from exc
    print(f'Updated {count} Champions learnsets in {FALLBACK_PATH}')
