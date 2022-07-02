import pathlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import click


@dataclass
class Match:
    line_no: int
    original_row: str
    updated_row: str


@click.command("far")
@click.argument("pattern", required=True, type=str)
@click.argument("replacement", required=True, type=str)
@click.argument("path", required=False, default=".", type=click.Path(exists=True))
def main(pattern: str, replacement: str, path: str) -> None:
    r: re.Pattern = re.compile(rf"{pattern}")
    files: List[pathlib.Path] = _collect_files(path)
    matches: Dict[str, List[Match]] = find_matches(files, r, replacement)
    replacements: Dict[str, List[Match]] = review_matches(matches)
    perform_replacement(replacements)


def _collect_files(path: str) -> List[pathlib.Path]:
    p: pathlib.Path = pathlib.Path(path)

    files: List[pathlib.Path]
    if p.is_dir():
        files = list(filter(lambda f: f.is_file(), [f for f in p.glob("**/*")]))
    else:
        files = [p]

    return files


def find_matches(
    files: List[pathlib.Path], pattern: re.Pattern, replacement: str
) -> Dict[str, List[Match]]:
    all_matches: Dict[str, List[Match]] = {}
    match_count: int = 0

    for file in files:
        matches: List[Match] = _find_matches(file, pattern, replacement)
        if matches:
            all_matches[file.as_posix()] = matches
            match_count += len(matches)

    click.secho(
        f"Found {match_count} matches across {len(all_matches)} files.", bold=True
    )

    return all_matches


def _find_matches(
    file: pathlib.Path, pattern: re.Pattern, replacement: str
) -> List[Match]:
    try:
        with open(file) as f:
            contents: List[str] = f.readlines()
    except UnicodeDecodeError:
        return []

    matches: List = []
    for line_no, row in enumerate(contents):
        match_parts: List[str] = pattern.split(row)
        if len(match_parts) > 1:
            updated_row = click.style(replacement, fg="red").join(
                m for m in match_parts
            )
            match: Match = Match(
                line_no=line_no,
                original_row=row,
                updated_row=updated_row,
            )
            matches.append(match)

    return matches


def review_matches(all_matches: Dict[str, List[Match]]) -> Dict[str, List[Match]]:
    all_replacements: Dict[str, List[Match]] = {}
    for file, matches in all_matches.items():
        replacements: List[Match] = _review_matches(file, matches)
        all_replacements[file] = replacements

    return all_replacements


def _review_matches(file: str, matches: List[Match]) -> List[Match]:
    replacements: List[Match] = []
    for match in matches:
        replace: bool = _review_match(file, match)
        if replace:
            replacements.append(match)

    return replacements


def _review_match(file: str, match: Match) -> bool:
    click.secho(f"\n{file}", fg="cyan")
    click.secho(f"{match.line_no + 1}", fg="yellow", nl=False)
    click.secho(f":{match.updated_row.strip()}")

    cmd: str
    replace: Optional[bool] = None
    while replace is None:
        cmd: str = input("\nCommand: ").lower()
        if cmd in {"", "y"}:
            replace = True
        elif cmd == "n":
            replace = False

    return replace


def perform_replacement(replacements: Dict[str, List[Match]]) -> None:
    for file, matches in replacements.items():
        _perform_replacement(file, matches)


def _perform_replacement(file: str, matches: List[Match]) -> None:
    with open(file, "r+") as f:
        contents: List[str] = f.readlines()

    for match in matches:
        line_no: int = match.line_no
        updated_row: str = match.updated_row
        contents[line_no] = updated_row

    f.writelines(contents)


if __name__ == "__main__":
    main()
