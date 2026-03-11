from pathlib import Path

import pytest

from py_local_git_pull.config.cli_parser import parse_args


def test_parse_args_should_normalize_and_dedupe_branches(tmp_path: Path) -> None:
    args = parse_args([str(tmp_path), "--branches", "main", "dev", "main"])

    assert args.path == str(tmp_path.resolve())
    assert args.branches == ["main", "dev"]
    assert args.output == "table"


@pytest.mark.parametrize(
    "argv",
    [
        ["/tmp", "--depth", "0"],
        ["/tmp", "--depth", "-1"],
        ["/tmp", "--max-depth", "-1"],
    ],
)
def test_parse_args_should_reject_invalid_numeric_values(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_args(argv)
