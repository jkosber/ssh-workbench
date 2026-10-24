"""Print a POSIX sh script that runs the key install command from login shells.

sshd runs a command as `<login shell> -c <command>`. For each shell named, the
printed script does the same twice, with HOME in a new temporary folder, so no
real `~/.ssh` is touched: the first run must install the key, the second must
find it. The key is fictional: fixed bytes in the OpenSSH public format, never
a usable key. This script runs nothing itself:

    uv run --locked python scripts/check_shells.py | ssh <approved target> sh -s
"""

import argparse
import base64
import re
import struct
import sys

from ssh_workbench.keys import PublicKey, posix_install_command

SHELLS = ("bash", "dash", "zsh", "fish", "tcsh")
# Ends the heredoc that holds the command; the command never contains it.
END = "SSH_WORKBENCH_COMMAND"


def shell_name(value: str) -> str:
    # Names are written into the printed script unquoted.
    if re.fullmatch(r"[A-Za-z0-9._+-]+", value) is None:
        raise argparse.ArgumentTypeError(f"not a shell name: {value!r}")
    return value


def fictional_key() -> PublicKey:
    data = (
        struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + bytes([7]) * 32
    )
    return PublicKey(
        "ssh-ed25519", base64.b64encode(data).decode(), "ssh-workbench-shell-check"
    )


def shell_script(shells: list[str]) -> str:
    key = fictional_key()
    installed = "SSH Workbench: key installed."
    found_again = "SSH Workbench: the key was already installed."
    return f"""command=$(cat <<'{END}'
{posix_install_command(key)}
{END}
)
key='{key.line}'
failed=0
for shell in {" ".join(shells)}; do
  if ! found=$(command -v "$shell"); then
    echo "$shell: not installed"
    failed=1
    continue
  fi
  home=$(mktemp -d) || exit 1
  first=$(HOME="$home" "$found" -c "$command" 2>"$home/stderr")
  second=$(HOME="$home" "$found" -c "$command" 2>>"$home/stderr")
  content=$(cat "$home/.ssh/authorized_keys" 2>/dev/null)
  if [ "$first" = "{installed}" ] &&
    [ "$second" = "{found_again}" ] &&
    [ "$content" = "$key" ]; then
    echo "$shell: PASS"
  else
    echo "$shell: FAIL"
    echo "  first run: $first"
    echo "  second run: $second"
    sed 's/^/  stderr: /' "$home/stderr"
    failed=1
  fi
  rm -rf "$home"
done
exit "$failed"
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shells",
        nargs="+",
        type=shell_name,
        default=list(SHELLS),
        help=f"shells to run the command from (default: {' '.join(SHELLS)})",
    )
    args = parser.parse_args()
    # sh on the other machine reads a CR as part of a word, so no CRLF.
    sys.stdout.reconfigure(newline="\n")
    print(shell_script(args.shells), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
