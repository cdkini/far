import logging
import pathlib
import re
from typing import List

import click


@click.command("far")
@click.argument("pattern", required=True, type=str)
@click.argument("replacement", required=True, type=str)
@click.argument("path", required=False, default=".", type=click.Path(exists=True))
def main(pattern: str, replacement: str, path: str) -> None:
    r: re.Pattern = re.compile(rf"{pattern}")

    files: List[pathlib.Path] = _collect_files(path)
    iterate(files, r, replacement)


def _collect_files(path: str) -> List[pathlib.Path]:
    p = pathlib.Path(path)

    files: List[pathlib.Path]
    if p.is_dir():
        files = list(filter(lambda f: f.is_file(), [f for f in p.glob("**/*")]))
    else:
        files = [p]

    return files


def iterate(files: List[pathlib.Path], pattern: re.Pattern, replacement: str) -> None:
    for file in files:
        _iterate(file, pattern, replacement)


def _iterate(file: pathlib.Path, pattern: re.Pattern, replacement: str) -> None:
    try:
        with open(file) as f:
            contents: List[str] = f.readlines()
    except UnicodeDecodeError:
        logging.warning(file)
        return

    for line_no, row in enumerate(contents):
        match = pattern.split(row)
        if len(match) > 1:
            foo = replacement.join(m for m in match)
            print(line_no, foo)


if __name__ == "__main__":

