#!/usr/bin/env python3
"""
Batch-create Repomix bundles from a JSON repo list.

Default output layout:

repomix/
  SomeGameOrProject/
    README.md
    repomix-output.xml
    repomix_stdout.txt
    repomix_stderr.txt

Usage:

  python app.py repos.json

Optional:

  python app.py repos.json --output-root repomix_n64
  python app.py repos.json --output-file repo.xml
  python app.py repos.json --style xml
  python app.py --write-example repos.example.json

JSON formats supported:

1) Simple list of repo objects:

[
  {
    "game_name": "SonicUnleashedRecompiled",
    "url": "https://github.com/hedge-dev/UnleashedRecomp"
  },
  {
    "game_name": "reNut",
    "url": "https://github.com/masterspike52/reNut"
  }
]

2) Simple list of repo URLs. Folder names are inferred from the repo URL:

[
  "https://github.com/hedge-dev/UnleashedRecomp",
  "https://github.com/masterspike52/reNut"
]

3) Object with global settings and repos:

{
  "output_root": "repomix_xbox360",
  "output_file_name": "repomix-output.xml",
  "style": "xml",
  "timeout_seconds": 1800,
  "install_timeout_seconds": 600,
  "repos": [
    {
      "game_name": "SonicUnleashedRecompiled",
      "url": "https://github.com/hedge-dev/UnleashedRecomp"
    }
  ]
}

Requirements:
  - Python 3.10+
  - Node.js/npm installed and available on PATH

The script will automatically install Repomix globally with:

  npm install -g repomix

if the Repomix CLI is missing.

Windows note:
  This version forces UTF-8 decoding for subprocess output so Repomix/npm output
  does not crash Python reader threads on systems using cp1252 by default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse


# Force UTF-8 behavior for child tools where possible.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("NPM_CONFIG_UNICODE", "true")


@dataclass(frozen=True)
class RepoJob:
    game_name: str
    url: str


@dataclass
class BatchConfig:
    repos: list[RepoJob]
    output_root: Path = Path("repomix")
    output_file_name: str = "repomix-output.xml"
    style: str = "xml"
    timeout_seconds: int = 60 * 30
    install_timeout_seconds: int = 60 * 10


SUBPROCESS_TEXT_KWARGS: dict[str, Any] = {
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
}


EXAMPLE_JSON: dict[str, Any] = {
    "output_root": "repomix_xbox360",
    "output_file_name": "repomix-output.xml",
    "style": "xml",
    "timeout_seconds": 1800,
    "install_timeout_seconds": 600,
    "repos": [
        {
            "game_name": "SonicUnleashedRecompiled",
            "url": "https://github.com/hedge-dev/UnleashedRecomp",
        },
        {
            "game_name": "reNut",
            "url": "https://github.com/masterspike52/reNut",
        },
        {
            "game_name": "TiP-Recomp",
            "url": "https://github.com/SolarCookies/TiP-Recomp",
        },
    ],
}


def safe_text(value: str | bytes | None) -> str:
    """
    Normalize subprocess output into safe UTF-8 text.

    TimeoutExpired can sometimes carry bytes depending on Python/platform behavior,
    so this makes logging robust either way.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def safe_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
    return cleaned or "UnnamedRepo"


def infer_game_name_from_url(url: str) -> str:
    """
    Infer a usable folder/project name from a GitHub URL.

    Examples:
      https://github.com/hedge-dev/UnleashedRecomp -> UnleashedRecomp
      https://github.com/foo/bar.git -> bar
    """
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]

    if path_parts:
        name = path_parts[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name or "UnnamedRepo"

    # Fallback for weird non-URL inputs.
    cleaned = url.rstrip("/").split("/")[-1]
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned or "UnnamedRepo"


def repo_job_from_item(item: Any, index: int) -> RepoJob:
    """
    Convert one JSON repo entry into a RepoJob.

    Supported:
      "https://github.com/org/repo"

      {
        "game_name": "MyProject",
        "url": "https://github.com/org/repo"
      }

      {
        "name": "MyProject",
        "repo": "https://github.com/org/repo"
      }
    """
    if isinstance(item, str):
        url = item.strip()
        if not url:
            raise ValueError(f"Repo entry #{index} is an empty string.")
        return RepoJob(game_name=infer_game_name_from_url(url), url=url)

    if not isinstance(item, dict):
        raise ValueError(
            f"Repo entry #{index} must be a string URL or object, got {type(item).__name__}."
        )

    url = (
        item.get("url")
        or item.get("repo")
        or item.get("github")
        or item.get("github_url")
        or item.get("remote")
    )

    if not isinstance(url, str) or not url.strip():
        raise ValueError(
            f"Repo entry #{index} is missing a valid repo URL. "
            "Use key 'url', 'repo', 'github', 'github_url', or 'remote'."
        )

    url = url.strip()

    game_name = (
        item.get("game_name")
        or item.get("name")
        or item.get("folder")
        or item.get("project")
        or infer_game_name_from_url(url)
    )

    if not isinstance(game_name, str) or not game_name.strip():
        game_name = infer_game_name_from_url(url)

    return RepoJob(game_name=game_name.strip(), url=url)


def load_batch_config(json_path: Path) -> BatchConfig:
    """
    Load repos and optional settings from a JSON file.
    """
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(f"JSON repo file not found: {json_path}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON in {json_path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from None

    if isinstance(raw, list):
        repo_items = raw
        output_root = Path("repomix")
        output_file_name = "repomix-output.xml"
        style = "xml"
        timeout_seconds = 60 * 30
        install_timeout_seconds = 60 * 10

    elif isinstance(raw, dict):
        repo_items = raw.get("repos")
        if not isinstance(repo_items, list):
            raise RuntimeError(
                f"{json_path} must contain a 'repos' array when using object format."
            )

        output_root = Path(str(raw.get("output_root", "repomix")))
        output_file_name = str(raw.get("output_file_name", "repomix-output.xml"))
        style = str(raw.get("style", "xml"))

        try:
            timeout_seconds = int(raw.get("timeout_seconds", 60 * 30))
            install_timeout_seconds = int(raw.get("install_timeout_seconds", 60 * 10))
        except ValueError:
            raise RuntimeError(
                "timeout_seconds and install_timeout_seconds must be integers."
            ) from None

    else:
        raise RuntimeError(
            f"{json_path} must be either a JSON array or a JSON object with a 'repos' array."
        )

    repos: list[RepoJob] = []
    seen_folders: set[str] = set()

    for index, item in enumerate(repo_items, start=1):
        job = repo_job_from_item(item, index)

        folder_key = safe_folder_name(job.game_name).lower()
        if folder_key in seen_folders:
            raise RuntimeError(
                f"Duplicate game/folder name after cleanup: {job.game_name!r}. "
                "Use unique 'game_name' values in the JSON."
            )
        seen_folders.add(folder_key)

        repos.append(job)

    if not repos:
        raise RuntimeError(f"No repos found in {json_path}.")

    if not output_file_name.strip():
        raise RuntimeError("output_file_name cannot be empty.")

    if timeout_seconds <= 0:
        raise RuntimeError("timeout_seconds must be greater than 0.")

    if install_timeout_seconds <= 0:
        raise RuntimeError("install_timeout_seconds must be greater than 0.")

    return BatchConfig(
        repos=repos,
        output_root=output_root,
        output_file_name=output_file_name,
        style=style,
        timeout_seconds=timeout_seconds,
        install_timeout_seconds=install_timeout_seconds,
    )


def apply_cli_overrides(config: BatchConfig, args: argparse.Namespace) -> BatchConfig:
    """
    CLI arguments override JSON global settings when provided.
    """
    if args.output_root is not None:
        config.output_root = Path(args.output_root)

    if args.output_file is not None:
        config.output_file_name = args.output_file

    if args.style is not None:
        config.style = args.style

    if args.timeout is not None:
        config.timeout_seconds = args.timeout

    if args.install_timeout is not None:
        config.install_timeout_seconds = args.install_timeout

    return config


def get_npm_global_bin() -> str | None:
    """
    Ask npm where global binaries are installed.

    This helps when npm successfully installs repomix globally,
    but the current shell PATH does not expose the npm global bin folder.
    """
    npm_exe = shutil.which("npm")
    if not npm_exe:
        return None

    try:
        result = subprocess.run(
            [npm_exe, "bin", "-g"],
            **SUBPROCESS_TEXT_KWARGS,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )

        candidate = result.stdout.strip()
        if result.returncode == 0 and candidate:
            return candidate

    except Exception:
        pass

    try:
        result = subprocess.run(
            [npm_exe, "prefix", "-g"],
            **SUBPROCESS_TEXT_KWARGS,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )

        prefix = result.stdout.strip()
        if result.returncode == 0 and prefix:
            if os.name == "nt":
                return prefix
            return str(Path(prefix) / "bin")

    except Exception:
        pass

    return None


def add_npm_global_bin_to_path() -> None:
    npm_bin = get_npm_global_bin()
    if not npm_bin:
        return

    current_path = os.environ.get("PATH", "")
    paths = current_path.split(os.pathsep)

    if npm_bin not in paths:
        os.environ["PATH"] = npm_bin + os.pathsep + current_path


def install_repomix_cli(config: BatchConfig) -> None:
    """
    Install Repomix globally using npm.

    Raises RuntimeError if npm is missing or installation fails.
    """
    npm_exe = shutil.which("npm")
    if not npm_exe:
        raise RuntimeError(
            "Repomix is not installed, and npm was not found on PATH.\n"
            "Install Node.js first, then rerun this script."
        )

    config.output_root.mkdir(parents=True, exist_ok=True)

    install_stdout = config.output_root / "repomix_install_stdout.txt"
    install_stderr = config.output_root / "repomix_install_stderr.txt"

    print("Repomix CLI not found. Installing with: npm install -g repomix")

    result = subprocess.run(
        [npm_exe, "install", "-g", "repomix"],
        **SUBPROCESS_TEXT_KWARGS,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=config.install_timeout_seconds,
        check=False,
    )

    install_stdout.write_text(safe_text(result.stdout), encoding="utf-8", errors="replace")
    install_stderr.write_text(safe_text(result.stderr), encoding="utf-8", errors="replace")

    if result.returncode != 0:
        raise RuntimeError(
            "npm failed to install Repomix globally.\n"
            f"Exit code: {result.returncode}\n"
            f"See logs:\n"
            f"  {install_stdout}\n"
            f"  {install_stderr}"
        )

    add_npm_global_bin_to_path()

    if not shutil.which("repomix"):
        raise RuntimeError(
            "npm reported success, but the 'repomix' command is still not on PATH.\n"
            "Try opening a new terminal, or add your npm global bin folder to PATH.\n"
            f"Install logs:\n"
            f"  {install_stdout}\n"
            f"  {install_stderr}"
        )

    print("Repomix CLI installed successfully.")


def find_or_install_repomix_command(config: BatchConfig) -> list[str]:
    """
    Ensure the Repomix CLI exists.

    Order:
      1. Check current PATH.
      2. Add npm global bin to PATH and check again.
      3. Install globally with npm install -g repomix.
      4. Verify again.
    """
    repomix_exe = shutil.which("repomix")
    if repomix_exe:
        return [repomix_exe]

    add_npm_global_bin_to_path()

    repomix_exe = shutil.which("repomix")
    if repomix_exe:
        return [repomix_exe]

    install_repomix_cli(config)

    repomix_exe = shutil.which("repomix")
    if repomix_exe:
        return [repomix_exe]

    raise RuntimeError("Repomix install completed, but repomix could not be found.")


def write_readme(
    folder: Path,
    job: RepoJob,
    config: BatchConfig,
    status: str,
    command: Sequence[str],
    return_code: int | None = None,
) -> None:
    readme = folder / "README.md"
    command_text = " ".join(command) if command else "Not run"

    lines = [
        f"# {job.game_name}",
        "",
        f"Original GitHub repo: {job.url}",
        "",
        f"Repomix status: **{status}**",
        "",
        f"Output file: `{config.output_file_name}`",
        "",
        "Command used:",
        "",
        "```bash",
        command_text,
        "```",
        "",
    ]

    if return_code is not None:
        lines.extend(
            [
                f"Repomix exit code: `{return_code}`",
                "",
            ]
        )

    readme.write_text("\n".join(lines), encoding="utf-8", errors="replace")


def run_repomix(job: RepoJob, config: BatchConfig, repomix_cmd: Sequence[str]) -> bool:
    folder = config.output_root / safe_folder_name(job.game_name)
    folder.mkdir(parents=True, exist_ok=True)

    output_path = folder / config.output_file_name
    stdout_path = folder / "repomix_stdout.txt"
    stderr_path = folder / "repomix_stderr.txt"
    error_path = folder / "ERROR.txt"

    command = [
        *repomix_cmd,
        "--remote",
        job.url,
        "--style",
        config.style,
        "-o",
        config.output_file_name,
    ]

    print(f"\n=== Processing: {job.game_name} ===")
    print(f"Repo: {job.url}")
    print(f"Folder: {folder}")

    write_readme(folder, job, config, "running", command)

    try:
        result = subprocess.run(
            command,
            cwd=folder,
            **SUBPROCESS_TEXT_KWARGS,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=config.timeout_seconds,
            check=False,
        )

        stdout_path.write_text(safe_text(result.stdout), encoding="utf-8", errors="replace")
        stderr_path.write_text(safe_text(result.stderr), encoding="utf-8", errors="replace")

        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            if error_path.exists():
                error_path.unlink()

            write_readme(folder, job, config, "success", command, result.returncode)
            print(f"[OK] Wrote {output_path}")
            return True

        error_text = (
            f"Repomix failed or did not create a valid output file.\n\n"
            f"Project: {job.game_name}\n"
            f"Repo: {job.url}\n"
            f"Exit code: {result.returncode}\n\n"
            f"See repomix_stdout.txt and repomix_stderr.txt in this folder.\n"
        )
        error_path.write_text(error_text, encoding="utf-8", errors="replace")
        write_readme(folder, job, config, "failed", command, result.returncode)
        print(f"[FAIL] {job.game_name} exited with code {result.returncode}")
        return False

    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(safe_text(exc.stdout), encoding="utf-8", errors="replace")
        stderr_path.write_text(safe_text(exc.stderr), encoding="utf-8", errors="replace")

        error_text = (
            f"Repomix timed out after {config.timeout_seconds} seconds.\n\n"
            f"Project: {job.game_name}\n"
            f"Repo: {job.url}\n\n"
            f"The script continued to the next repo.\n"
        )
        error_path.write_text(error_text, encoding="utf-8", errors="replace")
        write_readme(folder, job, config, "timed out", command)
        print(f"[TIMEOUT] {job.game_name}")
        return False

    except Exception as exc:
        error_text = (
            f"Unexpected Python-side error while running Repomix.\n\n"
            f"Project: {job.game_name}\n"
            f"Repo: {job.url}\n"
            f"Error type: {type(exc).__name__}\n"
            f"Error: {exc}\n\n"
            f"The script continued to the next repo.\n"
        )
        error_path.write_text(error_text, encoding="utf-8", errors="replace")
        write_readme(folder, job, config, "python error", command)
        print(f"[ERROR] {job.game_name}: {exc}")
        return False


def write_example_json(path: Path) -> None:
    path.write_text(
        json.dumps(EXAMPLE_JSON, indent=2) + "\n",
        encoding="utf-8",
        errors="replace",
    )
    print(f"Wrote example JSON: {path}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-create Repomix outputs from a JSON repo list."
    )

    parser.add_argument(
        "json_file",
        nargs="?",
        help="Path to repo JSON file. Example: repos.json",
    )

    parser.add_argument(
        "--write-example",
        metavar="PATH",
        help="Write an example JSON file and exit.",
    )

    parser.add_argument(
        "--output-root",
        help="Override output root folder from JSON. Example: repomix_n64",
    )

    parser.add_argument(
        "--output-file",
        help="Override Repomix output filename. Example: repomix-output.xml",
    )

    parser.add_argument(
        "--style",
        help="Override Repomix style. Default/json value is usually xml.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        help="Override per-repo Repomix timeout in seconds.",
    )

    parser.add_argument(
        "--install-timeout",
        type=int,
        help="Override npm install timeout in seconds.",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.write_example:
        write_example_json(Path(args.write_example))
        return 0

    if not args.json_file:
        print(
            "Fatal: Missing JSON repo file.\n\n"
            "Usage:\n"
            "  python app.py repos.json\n\n"
            "To create a starter file:\n"
            "  python app.py --write-example repos.example.json",
            file=sys.stderr,
        )
        return 1

    try:
        config = load_batch_config(Path(args.json_file))
        config = apply_cli_overrides(config, args)
    except RuntimeError as exc:
        print(f"Fatal: {exc}", file=sys.stderr)
        return 1

    config.output_root.mkdir(parents=True, exist_ok=True)

    try:
        repomix_cmd = find_or_install_repomix_command(config)
    except RuntimeError as exc:
        print(f"Fatal: {exc}", file=sys.stderr)
        return 1

    summary_lines: list[str] = [
        "# Repomix Batch Summary",
        "",
        f"Input JSON: `{args.json_file}`",
        f"Output root: `{config.output_root}`",
        f"Output file name: `{config.output_file_name}`",
        f"Repomix style: `{config.style}`",
        "",
        "| Status | Project | Repo |",
        "|---|---|---|",
    ]

    success_count = 0
    fail_count = 0

    for job in config.repos:
        ok = run_repomix(job, config, repomix_cmd)
        status = "OK" if ok else "FAILED"

        if ok:
            success_count += 1
        else:
            fail_count += 1

        summary_lines.append(f"| {status} | {job.game_name} | {job.url} |")

    summary_lines.extend(
        [
            "",
            f"Successful: **{success_count}**",
            f"Failed: **{fail_count}**",
            "",
            "Failures are non-fatal. Check each failed repo folder for `ERROR.txt`, "
            "`repomix_stdout.txt`, and `repomix_stderr.txt`.",
            "",
        ]
    )

    summary_path = config.output_root / "SUMMARY.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8", errors="replace")

    print("\n=== Done ===")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Summary: {summary_path}")

    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
