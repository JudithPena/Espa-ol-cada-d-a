"""Fail closed before uploading a Cloudflare Pages deployment directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HTML_LIMIT = 1_500_000
ASSET_LIMIT = 25 * 1024 * 1024
FILE_LIMIT = 20_000


def check_budget(directory: Path, *, html_limit=HTML_LIMIT, asset_limit=ASSET_LIMIT,
                 file_limit=FILE_LIMIT) -> dict:
    directory = Path(directory)
    files = [p for p in directory.rglob('*') if p.is_file()]
    index = directory / 'index.html'
    if not index.is_file():
        raise ValueError('Missing index.html')
    largest = max(files, key=lambda p: p.stat().st_size)
    report = {'html_bytes': index.stat().st_size, 'file_count': len(files),
              'total_bytes': sum(p.stat().st_size for p in files),
              'largest_asset': largest.relative_to(directory).as_posix(),
              'largest_bytes': largest.stat().st_size,
              'audio_files': sum(p.suffix == '.mp3' for p in files),
              'limits': {'html_bytes': html_limit, 'asset_bytes': asset_limit, 'files': file_limit}}
    errors = []
    if report['html_bytes'] > html_limit:
        errors.append(f"HTML {report['html_bytes']} > {html_limit} bytes")
    if report['largest_bytes'] > asset_limit:
        errors.append(f"Asset {report['largest_asset']} {report['largest_bytes']} > {asset_limit} bytes")
    if len(files) > file_limit:
        errors.append(f'Files {len(files)} > {file_limit}')
    if errors:
        raise ValueError('; '.join(errors))
    report['warnings'] = [f'{key}: over 80% of budget' for key, value, limit in
                          [('html', report['html_bytes'], html_limit),
                           ('asset', report['largest_bytes'], asset_limit),
                           ('files', len(files), file_limit)] if value >= limit * .8]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(check_budget(args.directory), indent=2, ensure_ascii=False))
    except ValueError as error:
        parser.exit(1, f'Static deployment budget failed: {error}\n')


if __name__ == '__main__':
    main()
