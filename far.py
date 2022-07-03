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
@click.option(
    "--interactive",
    "-I",
    "interactive",
    is_flag=True,
    help="Interactively review each proposed change.",
)
@click.option(
    "--preview",
    "-p",
    "preview",
    is_flag=True,
    help="Print proposed changes to stdout without writing to disk.",
)
def main(
    pattern: str, replacement: str, path: str, interactive: bool, preview: bool
) -> None:
    """
    far makes find-and-replace workflows from the terminal a breeze.
    """
    assert not (interactive and preview), "Cannot use -I and -P flags together"

    r: re.Pattern = re.compile(rf"{pattern}")
    files: List[pathlib.Path] = collect_files(path)
    matches: Dict[str, List[Match]] = find_matches(files, r, replacement)

    replacements: Dict[str, List[Match]]
    if interactive or preview:
        replacements = review_matches(matches, preview_only=preview)
    else:
        replacements = matches

    if not preview:
        perform_replacement(replacements)


def collect_files(path: str) -> List[pathlib.Path]:
    p: pathlib.Path = pathlib.Path(path)

    files: List[pathlib.Path]
    if p.is_dir():
        files = _collect_files_from_dir(p)
    else:
        files = [p]

    return files


def _collect_files_from_dir(directory: pathlib.Path) -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    for file in directory.glob("**/*"):
        if not file.is_file() or any(p[0] == "." and p[1] != "." for p in file.parts):
            continue
        files.append(file)

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
        updated_row: str = pattern.sub(replacement, string=row)
        if updated_row != row:
            match: Match = Match(
                line_no=line_no,
                original_row=row,
                updated_row=updated_row,
            )
            matches.append(match)

    return matches


def review_matches(
    all_matches: Dict[str, List[Match]], preview_only
) -> Dict[str, List[Match]]:
    all_replacements: Dict[str, List[Match]] = {}
    for file, matches in all_matches.items():
        replacements: List[Match] = _review_matches(file, matches, preview_only)
        all_replacements[file] = replacements

    return all_replacements


def _review_matches(file: str, matches: List[Match], preview_only: bool) -> List[Match]:
    replacements: List[Match] = []
    for match in matches:
        replace: bool = _review_match(file, match, preview_only)
        if replace:
            replacements.append(match)

    return replacements


def _review_match(file: str, match: Match, preview_only: bool) -> bool:
    click.secho(f"\n{file}:L{match.line_no + 1}", fg="yellow")
    stylized_original_row: str = click.style(f"-{match.original_row.strip()}", fg="red")
    click.secho(stylized_original_row)
    stylized_updated_row: str = click.style(f"+{match.updated_row.strip()}", fg="green")
    click.secho(stylized_updated_row)

    replace: Optional[bool] = None

    if preview_only:
        replace = False

    while replace is None:
        cmd: str = input("\nCommand: ").lower()
        if cmd in {"", "y"}:
            replace = True
        elif cmd == "n":
            replace = False

    return replace


def perform_replacement(replacements: Dict[str, List[Match]]) -> None:
    file_count: int = 0
    match_count: int = 0
    for file, matches in replacements.items():
        _perform_replacement(file, matches)
        file_count += 1
        match_count += len(matches)

    click.secho(
        f"\nPerformed {match_count} replacements across {file_count} files.", bold=True
    )


def _perform_replacement(file: str, matches: List[Match]) -> None:
    with open(file, "r+") as f:
        contents: List[str] = f.readlines()

        for match in matches:
            line_no: int = match.line_no
            updated_row: str = match.updated_row
            contents[line_no] = updated_row

        f.seek(0)
        f.writelines(contents)
        f.truncate()


if __name__ == "__main__":
    main()
