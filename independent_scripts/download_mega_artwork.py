#!/usr/bin/env python3
"""Download Serebii artwork for Gen 9 Mega forms in the bundled Pokédex."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import struct
import sys
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'images/pokemon_art/Generation 9 Pokémon/Megas'
SITE = 'https://www.serebii.net'


class ArtworkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        path = urlsplit(urljoin(SITE, attrs.get('src', ''))).path
        if tag == 'img' and re.fullmatch(r'/art/th/\d+-[a-z0-9-]+\.png', path):
            self.paths.add(path)


def targets(pokedex):
    return sorted((p for p in pokedex.values()
                   if p.get('num', 0) > 0 and 'Mega' in p.get('forme', '').split('-')
                   and (p.get('gen') == 9 or p['num'] >= 906)),
                  key=lambda p: (p['num'], p['name']))


def artwork_url(entry, html):
    parser = ArtworkParser()
    parser.feed(html)
    # Only map verified artwork conventions. Never use a sprite or a base form.
    suffix = {'Mega': 'm', 'Mega-X': 'mx', 'Mega-Y': 'my', 'Mega-Z': 'mz',
              'M-Mega': 'm', 'Curly-Mega': 'm'}.get(entry['forme'])
    if suffix is None:
        raise ValueError('No verified artwork mapping for this alternate form')
    wanted = f"{entry['num']}-{suffix}.png"
    matches = [p for p in parser.paths if Path(p).name.lstrip('0') == wanted]
    if len(matches) != 1:
        raise ValueError(f'Expected one artwork thumbnail for {wanted}; found {len(matches)}')
    return SITE + matches[0].replace('/art/th/', '/pokemon/art/')


def png_dimensions(data):
    if len(data) < 33 or data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        raise ValueError('Response is not a PNG image')
    width, height = struct.unpack('>II', data[16:24])
    if not width or not height or b'IEND' not in data[-12:]:
        raise ValueError('Incomplete PNG image')
    return width, height


class Fetcher:
    def __init__(self, delay):
        self.delay = delay
        self.last = 0

    def get(self, url):
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        request = Request(url, headers={'User-Agent': 'DamageAgent-ArtworkDownloader/1.0',
                                       'Referer': SITE + '/'})
        with urlopen(request, timeout=30) as response:
            return response.read()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--pokemon', action='append', help='Species or canonical form; repeatable')
    parser.add_argument('--dry-run', action='store_true', help='List targets without network or writes')
    parser.add_argument('--overwrite', action='store_true', help='Replace existing artwork')
    parser.add_argument('--delay', type=float, default=1.0, help='Seconds between requests (default: 1)')
    args = parser.parse_args(argv)
    if args.delay < 0:
        parser.error('--delay must be nonnegative')
    entries = targets(json.loads((ROOT / 'data/pokedex.json').read_text()))
    if args.pokemon:
        selected = {s.casefold() for s in args.pokemon}
        entries = [p for p in entries if selected & {p['name'].casefold(), p['baseSpecies'].casefold()}]
        matched = {s for s in selected for p in entries
                   if s in {p['name'].casefold(), p['baseSpecies'].casefold()}}
        if selected - matched:
            parser.error('Unknown Gen 9 Mega selection: ' + ', '.join(sorted(selected - matched)))
    fetcher, pages, results = Fetcher(args.delay), {}, []
    for entry in entries:
        filename = f"{entry['num']:04d} {entry['name'].replace('-', ' ')}.png"
        destination = args.output / filename
        record = {'name': entry['name'], 'file': filename}
        try:
            if destination.exists() and not args.overwrite:
                png_dimensions(destination.read_bytes())
                record['status'] = 'skipped'
            elif args.dry_run:
                record['status'] = 'planned'
            else:
                slug = entry['baseSpecies'].lower().replace(' ', '')
                page_url = f'{SITE}/pokedex-sv/{slug}/'
                record['page_url'] = page_url
                if page_url not in pages:
                    pages[page_url] = fetcher.get(page_url).decode('utf-8', errors='replace')
                url = artwork_url(entry, pages[page_url])
                record['image_url'] = url
                data = fetcher.get(url)
                record['dimensions'] = png_dimensions(data)
                args.output.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix('.png.part')
                try:
                    temporary.write_bytes(data)
                    temporary.replace(destination)
                finally:
                    temporary.unlink(missing_ok=True)
                record['status'] = 'downloaded'
        except (OSError, ValueError) as exc:
            record.update(status='failed', error=str(exc))
        results.append(record)
        print(f"{record['status']:10} {entry['name']}" +
              (f": {record['error']}" if 'error' in record else ''), flush=True)
    if not args.dry_run:
        args.output.mkdir(parents=True, exist_ok=True)
        manifest = args.output / 'serebii-download-report.json'
        manifest.write_text(json.dumps(results, indent=2) + '\n')
        print(f'Report: {manifest}')
        missing = args.output / 'missing-artwork.md'
        lines = ['# Artwork needing manual download', '',
                 'Failed downloads from the latest run; these may be network errors or unmapped variants.', '']
        for result in results:
            if result['status'] == 'failed':
                lines.append(f"- [{result['name']}]({result.get('page_url', SITE)}) — {result['error']}. Save as `{result['file']}`.")
        if not any(result['status'] == 'failed' for result in results):
            lines.append('None.')
        missing.write_text('\n'.join(lines) + '\n')
        print(f'Missing artwork: {missing}')
    print(', '.join(f'{sum(r["status"] == status for r in results)} {status}'
                    for status in ('downloaded', 'skipped', 'planned', 'failed')))
    return int(any(r['status'] == 'failed' for r in results))


if __name__ == '__main__':
    sys.exit(main())
