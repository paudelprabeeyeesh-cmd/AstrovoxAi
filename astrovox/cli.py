"""Command line interface for Astrovox.

    astrovox login                  store a Hugging Face token
    astrovox push <repo>            upload the latest trained checkpoint
    astrovox pull <repo>            download a model repository
    astrovox list-models             browse models on the Hub
    astrovox card <repo>            render the model card without pushing
    astrovox checkpoints [dir]      list the checkpoints found locally
    astrovox whoami                 show the authenticated account
    astrovox logout                 forget the stored token

Exit status is 0 on success and 1 on failure, so the commands compose in a
script without parsing messages.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from astrovox.hub import (
    AuthenticationError,
    CheckpointNotFound,
    HubError,
    RepositoryNotFound,
    build_card,
    collect_bundle,
    find_checkpoints,
    list_models,
    login,
    logout,
    normalize_repo_id,
    pull_model,
    push_model,
    status,
    whoami,
)


def _emit(message: str) -> None:
    """Write a progress line to standard error, leaving stdout for results."""
    print(message, file=sys.stderr, flush=True)


def cmd_login(args: argparse.Namespace) -> int:
    """Store an access token."""
    token = args.token
    if not token and sys.stdin.isatty():
        _emit("Paste your Hugging Face token (it will not be echoed):")
        import getpass

        token = getpass.getpass().strip()
    if not token:
        _emit("No token supplied. Pass one as an argument or pipe it in.")
        return 1

    identity = login(token, path=args.token_file)
    _emit(f"Token stored for {identity.username}")
    if identity.token:
        _emit(f"Token: {identity.token[:8]}...")
    return 0


def cmd_logout(args: argparse.Namespace) -> int:
    """Remove the stored token."""
    removed = logout(path=args.token_file)
    _emit("Token removed" if removed else "No token was stored")
    return 0


def cmd_whoami(args: argparse.Namespace) -> int:
    """Show which account is authenticated."""
    current = status(path=args.token_file)
    if not current["authenticated"]:
        _emit("Not authenticated. Run 'astrovox login' first.")
        return 1
    try:
        identity = whoami(path=args.token_file)
        print(identity.username)
        return 0
    except AuthenticationError as exc:
        _emit(str(exc))
        return 1


def cmd_push(args: argparse.Namespace) -> int:
    """Upload the latest checkpoint to a repository."""
    try:
        result = push_model(
            args.repo,
            root=args.path,
            checkpoint=args.checkpoint,
            token=args.token,
            private=args.private,
            commit_message=args.message,
            staging=args.staging,
            progress=None if args.quiet else _emit,
        )
    except CheckpointNotFound as exc:
        _emit(str(exc))
        return 1
    except HubError as exc:
        _emit(str(exc))
        return 1

    if not args.quiet:
        _emit(f"Pushed {len(result.uploaded)} file(s) to {result.url}")
    print(result.url)
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    """Download a repository."""
    try:
        result = pull_model(
            args.repo,
            directory=args.path,
            token=args.token,
            revision=args.revision,
            progress=None if args.quiet else _emit,
        )
    except (HubError, RepositoryNotFound) as exc:
        _emit(str(exc))
        return 1
    if not args.quiet:
        _emit(f"Downloaded {len(result.files)} file(s) to {result.directory}")
    print(result.directory)
    return 0


def cmd_list_models(args: argparse.Namespace) -> int:
    """List models on the Hub."""
    try:
        models = list_models(
            author=args.author, search=args.search, limit=args.limit, token=args.token
        )
    except HubError as exc:
        _emit(str(exc))
        return 1

    if not models:
        _emit("No models matched.")
        return 0
    header = f"{'model':<48}{'downloads':>12}{'likes':>8}  updated"
    print(header)
    print("-" * len(header))
    for model in models:
        print(
            f"{model['id']:<48}{model['downloads']:>12,}{model['likes']:>8}  "
            f"{model['last_modified'][:10]}"
        )
    return 0


def cmd_card(args: argparse.Namespace) -> int:
    """Print the model card that a push would produce."""
    try:
        bundle = collect_bundle(args.path, args.checkpoint)
    except CheckpointNotFound as exc:
        _emit(str(exc))
        return 1

    from astrovox.hub.card import ModelInfo

    info = ModelInfo.from_bundle(normalize_repo_id(args.repo or "local/model"), bundle)
    if args.parameter_count and not info.parameter_count:
        _emit("Note: no parameter count was found in the checkpoint manifest.")
    print(build_card(info, filename="model.avz"))
    return 0


def cmd_checkpoints(args: argparse.Namespace) -> int:
    """List the checkpoints found in a directory."""
    try:
        found = find_checkpoints(args.path)
    except CheckpointNotFound as exc:
        _emit(str(exc))
        return 1
    if not found:
        _emit(f"No checkpoints found under {args.path}")
        return 1
    header = f"{'file':<52}{'size MB':>10}  modified"
    print(header)
    print("-" * len(header))
    for entry in found[: args.limit]:
        stamp = __import__("datetime").datetime.fromtimestamp(entry.modified).strftime("%Y-%m-%d %H:%M")
        print(f"{entry.name:<52}{entry.size_mb:>10.2f}  {stamp}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the command line."""
    parser = argparse.ArgumentParser(
        prog="astrovox",
        description="Train, publish and manage Astrovox models.",
    )
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    sub = parser.add_subparsers(dest="command")

    def add_token_options(target: argparse.ArgumentParser) -> None:
        target.add_argument("--token", help="access token (defaults to the stored one)")
        target.add_argument("--token-file", help="path to the token file")

    login_parser = sub.add_parser("login", help="store a Hugging Face access token")
    login_parser.add_argument("token", nargs="?", help="the token to store")
    login_parser.add_argument("--token-file", help="path to the token file")
    login_parser.set_defaults(func=cmd_login)

    logout_parser = sub.add_parser("logout", help="remove the stored token")
    logout_parser.add_argument("--token-file")
    logout_parser.set_defaults(func=cmd_logout)

    whoami_parser = sub.add_parser("whoami", help="show the authenticated account")
    whoami_parser.add_argument("--token-file")
    whoami_parser.set_defaults(func=cmd_whoami)

    push_parser = sub.add_parser("push", help="upload the latest checkpoint")
    push_parser.add_argument("repo", help="repository id, for example my-user/astrovox-model")
    push_parser.add_argument("--path", default=".", help="directory to search for a checkpoint")
    push_parser.add_argument("--checkpoint", help="explicit checkpoint file")
    push_parser.add_argument("--private", action="store_true", help="create the repository as private")
    push_parser.add_argument("--message", help="commit message")
    push_parser.add_argument("--staging", help="assemble files here instead of a temporary directory")
    push_parser.add_argument("--quiet", action="store_true", help="suppress progress output")
    add_token_options(push_parser)
    push_parser.set_defaults(func=cmd_push)

    pull_parser = sub.add_parser("pull", help="download a model repository")
    pull_parser.add_argument("repo", help="repository id")
    pull_parser.add_argument("--path", help="directory to download into")
    pull_parser.add_argument("--revision", help="branch, tag or commit")
    pull_parser.add_argument("--quiet", action="store_true")
    add_token_options(pull_parser)
    pull_parser.set_defaults(func=cmd_pull)

    list_parser = sub.add_parser("list-models", help="list models on the Hub")
    list_parser.add_argument("--author", help="restrict to one author")
    list_parser.add_argument("--search", help="search term")
    list_parser.add_argument("--limit", type=int, default=25, help="how many to show")
    list_parser.add_argument("--token")
    list_parser.set_defaults(func=cmd_list_models)

    card_parser = sub.add_parser("card", help="print the model card without pushing")
    card_parser.add_argument("repo", nargs="?", help="repository id to use in the card")
    card_parser.add_argument("--path", default=".", help="directory to search")
    card_parser.add_argument("--checkpoint", help="explicit checkpoint file")
    card_parser.add_argument("--parameter-count", action="store_true", help="report the parameter count")
    card_parser.set_defaults(func=cmd_card)

    checkpoints_parser = sub.add_parser("checkpoints", help="list local checkpoints")
    checkpoints_parser.add_argument("path", nargs="?", default=".")
    checkpoints_parser.add_argument("--limit", type=int, default=30)
    checkpoints_parser.set_defaults(func=cmd_checkpoints)

    init_parser = sub.add_parser("init", help="initialize a new Astrovox project")
    init_parser.add_argument("path", nargs="?", default=".", help="target directory")
    init_parser.set_defaults(func=cmd_init)

    build_parser_cmd = sub.add_parser("build", help="build the current project")
    build_parser_cmd.add_argument("--target", default="production", help="build target")
    build_parser_cmd.set_defaults(func=cmd_build)

    test_parser_cmd = sub.add_parser("test", help="run tests")
    test_parser_cmd.add_argument("path", nargs="?", default="tests", help="test path")
    test_parser_cmd.set_defaults(func=cmd_test)

    benchmark_parser_cmd = sub.add_parser("benchmark", help="run benchmarks")
    benchmark_parser_cmd.add_argument("--suite", default="core", help="benchmark suite")
    benchmark_parser_cmd.set_defaults(func=cmd_benchmark)

    deploy_parser_cmd = sub.add_parser("deploy", help="deploy the project")
    deploy_parser_cmd.add_argument("target", help="deployment target")
    deploy_parser_cmd.set_defaults(func=cmd_deploy)

    doctor_parser_cmd = sub.add_parser("doctor", help="check project health")
    doctor_parser_cmd.set_defaults(func=cmd_doctor)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if getattr(args, "version", False):
        from astrovox import __version__

        print(__version__)
        return 0

    if not getattr(args, "func", None):
        parser.print_help()
        return 0

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        _emit("Interrupted.")
        return 130
    except (HubError, AuthenticationError, CheckpointNotFound) as exc:
        _emit(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())