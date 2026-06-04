# Repomixr

A small Python utility for batch-generating [Repomix](https://repomix.com/) bundles from a JSON list of GitHub repositories.

It was originally made for Xbox 360 recompilation projects, but it is now generic and can be used for:

- Xbox 360 recomp repos
- N64 recomp repos
- decompilation projects
- modding projects
- tool repos
- any public GitHub repo you want to pack into a Repomix file

The script reads a JSON file, creates one output folder per repo, runs Repomix against each remote GitHub repo, writes a `README.md` for each project, saves stdout/stderr logs, and continues gracefully if one repo fails.

---

## What This Script Does

Given a JSON file like this:

```json
{
  "output_root": "repomix_xbox360",
  "output_file_name": "repomix-output.xml",
  "style": "xml",
  "timeout_seconds": 1800,
  "install_timeout_seconds": 600,
  "remove_comments": false,
  "remove_empty_lines": false,
  "output_show_line_numbers": false,
  "parsable_style": false,
  "compress": false,
  "repos": [
    {
      "game_name": "SonicUnleashedRecompiled",
      "url": "https://github.com/hedge-dev/UnleashedRecomp"
    },
    {
      "game_name": "reNut",
      "url": "https://github.com/masterspike52/reNut"
    }
  ]
}
```

It creates:

```text
repomix_xbox360/
  SonicUnleashedRecompiled/
    README.md
    repomix-output.xml
    repomix_stdout.txt
    repomix_stderr.txt

  reNut/
    README.md
    repomix-output.xml
    repomix_stdout.txt
    repomix_stderr.txt

  SUMMARY.md
```

Each generated project folder contains:

| File | Purpose |
|---|---|
| `README.md` | Project-specific note with the original GitHub repo link, Repomix status, output file name, command used, and exit code. |
| `repomix-output.xml` | The Repomix bundle generated for that repo. The filename can be changed in JSON or CLI args. |
| `repomix_stdout.txt` | Captured standard output from Repomix. |
| `repomix_stderr.txt` | Captured standard error from Repomix. |
| `ERROR.txt` | Only written when Repomix fails, times out, or the Python wrapper hits an unexpected error. |
| `SUMMARY.md` | Batch-wide summary written to the output root folder. |

---

## Requirements

### Required

- Python 3.10 or newer
- Node.js and npm available on PATH
- Internet access
- GitHub repos must be public or otherwise accessible to Repomix

### Repomix Installation

The script automatically checks whether the `repomix` CLI is installed.

If missing, it tries to install it with:

```bash
npm install -g repomix
```

If npm is missing, the script stops with a clear error telling you to install Node.js first.

---

## Files

Recommended files:

```text
repomix_batch_from_json.py
xbox360_playable_recomps.json
README.md
```

You can rename the JSON file to anything, such as:

```text
n64_recomps.json
xbox360_recomps.json
general_tools.json
my_repos.json
```

---

## Quick Start

### 1. Create or edit a JSON repo list

Example:

```json
{
  "output_root": "repomix_xbox360",
  "output_file_name": "repomix-output.xml",
  "style": "xml",
  "timeout_seconds": 1800,
  "install_timeout_seconds": 600,
  "remove_comments": false,
  "remove_empty_lines": false,
  "output_show_line_numbers": false,
  "parsable_style": false,
  "compress": false,
  "repos": [
    {
      "game_name": "SonicUnleashedRecompiled",
      "url": "https://github.com/hedge-dev/UnleashedRecomp"
    },
    {
      "game_name": "reNut",
      "url": "https://github.com/masterspike52/reNut"
    }
  ]
}
```

### 2. Run the script

```bash
python repomixr.py xbox360_playable_recomps.json
```

### 3. Check the output folder

```text
repomix_xbox360/
```

Inside that folder, check:

```text
SUMMARY.md
```

For failed repos, check the repo-specific folder:

```text
ERROR.txt
repomix_stdout.txt
repomix_stderr.txt
```

---

## JSON Formats Supported

The script supports three JSON formats.

---

### Format 1: Full Config Object

This is the recommended format.

```json
{
  "output_root": "repomix_xbox360",
  "output_file_name": "repomix-output.xml",
  "style": "xml",
  "timeout_seconds": 1800,
  "install_timeout_seconds": 600,
  "remove_comments": false,
  "remove_empty_lines": false,
  "output_show_line_numbers": false,
  "parsable_style": false,
  "compress": false,
  "repos": [
    {
      "game_name": "SonicUnleashedRecompiled",
      "url": "https://github.com/hedge-dev/UnleashedRecomp"
    },
    {
      "game_name": "reNut",
      "url": "https://github.com/masterspike52/reNut"
    }
  ]
}
```

#### Top-Level Fields

| Field | Required | Default | Description |
|---|---:|---|---|
| `output_root` | No | `repomix` | Root folder where all repo folders are created. |
| `output_file_name` | No | `repomix-output.xml` | Name of the generated Repomix file inside each project folder. |
| `style` | No | `xml` | Repomix output style passed to `--style`. |
| `timeout_seconds` | No | `1800` | Per-repo timeout in seconds. Default is 30 minutes. |
| `install_timeout_seconds` | No | `600` | Timeout for `npm install -g repomix`. Default is 10 minutes. |
| `remove_comments` | No | `false` | Passes `--remove-comments` to Repomix. |
| `remove_empty_lines` | No | `false` | Passes `--remove-empty-lines` to Repomix. |
| `output_show_line_numbers` | No | `false` | Passes `--output-show-line-numbers` to Repomix. |
| `parsable_style` | No | `false` | Passes `--parsable-style` to Repomix. |
| `compress` | No | `false` | Passes `--compress` to Repomix. |
| `repos` | Yes | none | Array of repo entries. |

#### Repo Object Fields

| Field | Required | Description |
|---|---:|---|
| `game_name` | Recommended | Folder/display name for the repo. |
| `url` | Yes | GitHub repo URL. |

The script also accepts alternative key names.

For the repo URL, these are accepted:

```text
url
repo
github
github_url
remote
```

For the project/folder name, these are accepted:

```text
game_name
name
folder
project
```

Example:

```json
{
  "repos": [
    {
      "name": "MyProject",
      "repo": "https://github.com/example/MyProject"
    }
  ]
}
```

---

### Format 2: Simple Object List

You can use just an array of repo objects:

```json
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
```

When using this format, defaults are used:

```text
output_root: repomix
output_file_name: repomix-output.xml
style: xml
timeout_seconds: 1800
install_timeout_seconds: 600
```

---

### Format 3: URL-Only List

You can provide only URLs:

```json
[
  "https://github.com/hedge-dev/UnleashedRecomp",
  "https://github.com/masterspike52/reNut"
]
```

The script infers the folder name from the repo URL.

For example:

```text
https://github.com/hedge-dev/UnleashedRecomp
```

becomes:

```text
UnleashedRecomp
```

This is useful for quick batch runs, but the full config format is better when you want clean folder names.

---

## Command-Line Usage

### Basic

```bash
python repomixr.py repos.json
```

### Write an example JSON file

```bash
python repomixr.py --write-example repos.example.json
```

### Override the output folder

```bash
python repomixr.pyrepos.json --output-root repomix_n64
```

### Override the Repomix output filename

```bash
python repomixr.py repos.json --output-file n64-repomix.xml
```

### Override Repomix style

```bash
python repomixr.py repos.json --style xml
```

### Override timeout

```bash
python repomixr.py repos.json --timeout 3600
```

### Override Repomix install timeout

```bash
python repomixr.py repos.json --install-timeout 1200
```

### Remove comments

```bash
python repomixr.py repos.json --remove-comments
```

### Remove empty lines

```bash
python repomixr.py repos.json --remove-empty-lines
```

### Show line numbers in output

```bash
python repomixr.py repos.json --output-show-line-numbers
```

### Use parsable style

```bash
python repomixr.py repos.json --parsable-style
```

### Compress output

```bash
python repomixr.py repos.json --compress
```

### Combine optional Repomix flags

```bash
python repomixr.py repos.json --remove-comments --remove-empty-lines --compress
```

You can also enable these from JSON:

```json
{
  "output_root": "repomix_clean",
  "remove_comments": true,
  "remove_empty_lines": true,
  "output_show_line_numbers": true,
  "parsable_style": false,
  "compress": true,
  "repos": [
    {
      "game_name": "SomeProject",
      "url": "https://github.com/example/SomeProject"
    }
  ]
}
```


### Combined example

```bash
python repomixr.py n64_recomps.json --output-root repomix_n64 --timeout 3600
```

---

## Example: Xbox 360 Recomp JSON

```json
{
  "output_root": "repomix_xbox360",
  "output_file_name": "repomix-output.xml",
  "style": "xml",
  "timeout_seconds": 1800,
  "install_timeout_seconds": 600,
  "remove_comments": false,
  "remove_empty_lines": false,
  "output_show_line_numbers": false,
  "parsable_style": false,
  "compress": false,
  "repos": [
    {
      "game_name": "SonicUnleashedRecompiled",
      "url": "https://github.com/hedge-dev/UnleashedRecomp"
    },
    {
      "game_name": "reNut",
      "url": "https://github.com/masterspike52/reNut"
    },
    {
      "game_name": "TiP-Recomp",
      "url": "https://github.com/SolarCookies/TiP-Recomp"
    },
    {
      "game_name": "KameoRePowered",
      "url": "https://github.com/birabittoh/KameoRePowered"
    }
  ]
}
```

Run:

```bash
python repomixr.py xbox360_playable_recomps.json
```

---

## Example: N64 Recomp JSON

```json
{
  "output_root": "repomix_n64",
  "output_file_name": "repomix-output.xml",
  "style": "xml",
  "timeout_seconds": 1800,
  "install_timeout_seconds": 600,
  "remove_comments": false,
  "remove_empty_lines": false,
  "output_show_line_numbers": false,
  "parsable_style": false,
  "compress": false,
  "repos": [
    {
      "game_name": "Zelda64Recomp",
      "url": "https://github.com/Zelda64Recomp/Zelda64Recomp"
    },
    {
      "game_name": "DinoRecomp",
      "url": "https://github.com/dinosaurmod/DinoRecomp"
    }
  ]
}
```

Run:

```bash
python repomixr.py n64_recomps.json
```

---

## Example: General Tool Repo JSON

```json
{
  "output_root": "repomix_tools",
  "repos": [
    {
      "game_name": "Repomix",
      "url": "https://github.com/yamadashy/repomix"
    },
    {
      "game_name": "Ghidra",
      "url": "https://github.com/NationalSecurityAgency/ghidra"
    }
  ]
}
```

Run:

```bash
python repomixr.py tools.json
```

---

## How the Script Works

For each repo entry, the script:

1. Validates the JSON entry.
2. Creates a safe folder name from `game_name`.
3. Creates the output folder under `output_root`.
4. Writes an initial `README.md` with status `running`.
5. Runs Repomix with:

```bash
repomix --remote <repo-url> --style <style> -o <output-file-name>
```

When enabled, the script appends any of these optional flags:

```bash
--remove-comments
--remove-empty-lines
--output-show-line-numbers
--parsable-style
--compress
```

6. Saves Repomix stdout to:

```text
repomix_stdout.txt
```

7. Saves Repomix stderr to:

```text
repomix_stderr.txt
```

8. Checks whether the output file exists and is non-empty.
9. Updates the project `README.md` with final status.
10. Continues to the next repo even if the current one fails.
11. Writes a batch-wide `SUMMARY.md`.

---

## Error Handling

The script is designed to continue even when individual repos fail.

A repo is marked failed if:

- Repomix exits with a non-zero code.
- Repomix does not create the expected output file.
- Repomix creates an empty output file.
- The repo times out.
- A Python-side exception occurs while processing that repo.

For a failed repo, the script writes:

```text
ERROR.txt
repomix_stdout.txt
repomix_stderr.txt
README.md
```

The batch continues with the next repo.

At the end, the script exits with:

| Exit Code | Meaning |
|---:|---|
| `0` | All repos succeeded. |
| `1` | Fatal setup/config error before processing repos. |
| `2` | One or more repos failed, but the batch completed. |

---

## Windows UTF-8 Fix

This script includes a Windows-safe subprocess decoding fix.

It sets:

```python
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("NPM_CONFIG_UNICODE", "true")
```

And all subprocess calls use:

```python
text=True
encoding="utf-8"
errors="replace"
```

This avoids errors like:

```text
UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f
```

That error can happen on Windows because Python may try to decode Repomix/npm output using `cp1252` instead of UTF-8.

---

## Duplicate Folder Protection

The script prevents accidental folder collisions.

For example, these two entries would collide after folder-name cleanup:

```json
[
  {
    "game_name": "My Project",
    "url": "https://github.com/example/repo1"
  },
  {
    "game_name": "My_Project",
    "url": "https://github.com/example/repo2"
  }
]
```

Both become:

```text
My_Project
```

The script detects this and stops with a clear error.

To fix it, give each repo a unique `game_name`.

---

## Folder Name Cleanup

Folder names are sanitized for Windows/Linux compatibility.

The script replaces invalid characters such as:

```text
< > : " / \ | ? *
```

It also removes unsafe leading/trailing dots, spaces, and underscores.

Example:

```text
Banjo-Kazooie: Nuts & Bolts / reNut
```

becomes something safe like:

```text
Banjo-Kazooie_ Nuts & Bolts _ reNut
```

For best results, use clean names manually:

```json
{
  "game_name": "reNut",
  "url": "https://github.com/masterspike52/reNut"
}
```

---

## Troubleshooting

### `Fatal: Missing JSON repo file`

You ran the script without a JSON file.

Use:

```bash
python repomixr.py repos.json
```

Or create an example:

```bash
python repomixr.py --write-example repos.example.json
```

---

### `Repomix is not installed, and npm was not found on PATH`

Node.js/npm is missing or not on PATH.

Install Node.js, then reopen your terminal or IDE and run again.

Check:

```bash
node --version
npm --version
```

---

### `npm failed to install Repomix globally`

Check:

```text
repomix_install_stdout.txt
repomix_install_stderr.txt
```

These files are written under your configured output root.

Common causes:

- npm is broken or outdated
- no internet access
- permission problem with global npm installs
- antivirus blocked npm
- corporate/network proxy issue

You can manually install Repomix:

```bash
npm install -g repomix
```

Then rerun the script.

---

### `npm reported success, but the 'repomix' command is still not on PATH`

npm installed Repomix, but your current shell does not see the npm global binary folder.

Try:

1. Close and reopen your terminal or IDE.
2. Check where npm installs global binaries:

```bash
npm prefix -g
```

3. Add that folder to PATH.

On Windows, it is often something like:

```text
C:\Users\<YourUser>\AppData\Roaming\npm
```

---

### Repo times out

Increase the timeout:

```bash
python repomixr.py repos.json --timeout 3600
```

Or in JSON:

```json
{
  "timeout_seconds": 3600,
  "repos": []
}
```

---

### Repo fails but the batch keeps going

That is expected.

Check the failed repo folder:

```text
ERROR.txt
repomix_stdout.txt
repomix_stderr.txt
```

Then check:

```text
SUMMARY.md
```

---

### Output file missing or empty

The script treats this as a failure even if Repomix exits cleanly.

This protects against false positives.

Check:

```text
repomix_stdout.txt
repomix_stderr.txt
```

---

## Recommended Workflow

### For Xbox 360 Recomps

Use:

```text
xbox360_playable_recomps.json
```

with:

```json
"output_root": "repomix_xbox360"
```

Run:

```bash
python repomixr.py xbox360_playable_recomps.json
```

---

### For N64 Recomps

Create:

```text
n64_recomps.json
```

with:

```json
"output_root": "repomix_n64"
```

Run:

```bash
python repomixr.py n64_recomps.json
```

---

### For General Repos

Create:

```text
repos.json
```

Use either full objects:

```json
[
  {
    "game_name": "SomeProject",
    "url": "https://github.com/example/SomeProject"
  }
]
```

or URL-only entries:

```json
[
  "https://github.com/example/SomeProject"
]
```

Run:

```bash
python repomixr.py repos.json
```

---

## Notes and Limitations

- The script does not clone repos itself. It delegates remote repo processing to Repomix using `--remote`.
- Private repos may require extra authentication support from your local Repomix/GitHub setup.
- Very large repos may take a long time or exceed Repomix limits.
- Generated Repomix files can be large.
- The script does not delete old outputs before rerunning.
- If you rerun the same JSON, existing project folders may be overwritten or updated.
- The script assumes Repomix supports the selected `--style` value.
- The default style is `xml` because it is useful for AI/code-review workflows.

---

## Suggested Project Layout

```text
my-repomix-batches/
  repomix_batch_from_json.py
  README.md

  lists/
    xbox360_playable_recomps.json
    n64_recomps.json
    tools.json

  output/
    repomix_xbox360/
    repomix_n64/
    repomix_tools/
```

You can use CLI overrides to keep outputs organized:

```bash
python repomixr.py lists/xbox360_playable_recomps.json --output-root output/repomix_xbox360
python repomixr.py lists/n64_recomps.json --output-root output/repomix_n64
python repomixr.py lists/tools.json --output-root output/repomix_tools
```

---

## License / Ownership Note

This script only creates local Repomix bundles from repository contents available through the provided GitHub URLs.

The generated output may include source code, documentation, and project files from the original repositories. Always respect each original repository's license and usage terms.

Each generated project folder includes a `README.md` with the original GitHub repo link so the source remains traceable.

---

## Minimal Example

`repos.json`:

```json
[
  "https://github.com/hedge-dev/UnleashedRecomp",
  "https://github.com/masterspike52/reNut"
]
```

Run:

```bash
python repomixr.py repos.json
```

Output:

```text
repomix/
  UnleashedRecomp/
    README.md
    repomix-output.xml
    repomix_stdout.txt
    repomix_stderr.txt

  reNut/
    README.md
    repomix-output.xml
    repomix_stdout.txt
    repomix_stderr.txt

  SUMMARY.md
```
