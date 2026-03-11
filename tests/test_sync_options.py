from argparse import Namespace

from py_local_git_pull.core.sync_options import SyncOptions


def test_from_cli_args_should_convert_namespace_to_typed_options() -> None:
    args = Namespace(
        path="/tmp/demo",
        recursive=True,
        max_depth=5,
        branch="main",
        branches=["main", "dev"],
        auto_upstream=True,
        skip_non_exist=False,
        depth=3,
        no_stash=True,
        verbose=True,
        output="json",
    )

    options = SyncOptions.from_cli_args(args)

    assert options.path == "/tmp/demo"
    assert options.recursive is True
    assert options.max_depth == 5
    assert options.branch == "main"
    assert options.branches == ("main", "dev")
    assert options.auto_upstream is True
    assert options.skip_non_exist is False
    assert options.depth == 3
    assert options.no_stash is True
    assert options.verbose is True
    assert options.output == "json"
