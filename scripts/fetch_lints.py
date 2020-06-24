import json
import os
import re
import subprocess

import sys

"""
This script serves to download actual lints from rustc and clippy.
You need to have `rustc` and `git` available in $PATH for it to work.
"""

DIR = os.path.dirname(os.path.abspath(__name__))


class LintParsingMode:
    Start = 0
    ParsingLints = 1
    LintsParsed = 2
    ParsingGroups = 3


def get_rustc_lints():
    result = subprocess.run(["rustc", "-W", "help"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL,
                            check=True)
    output = result.stdout.decode()

    def normalize(name):
        return name.replace("-", "_")

    lint_regex = re.compile(r"^([a-z0-9]+-)*[a-z0-9]+$")
    parsing = LintParsingMode.Start
    lints = []
    for line in output.splitlines():
        line_parts = [part.strip() for part in line.strip().split()]
        if len(line_parts) == 0:
            if parsing == LintParsingMode.ParsingLints:
                parsing = LintParsingMode.LintsParsed
            continue
        if "----" in line_parts[0]:
            if parsing == LintParsingMode.Start:
                parsing = LintParsingMode.ParsingLints
            elif parsing == LintParsingMode.LintsParsed:
                parsing = LintParsingMode.ParsingGroups
            continue
        if parsing == LintParsingMode.ParsingLints and lint_regex.match(line_parts[0]):
            lints.append((normalize(line_parts[0]), False))
        if parsing == LintParsingMode.ParsingGroups and lint_regex.match(line_parts[0]):
            lints.append((normalize(line_parts[0]), True))
    return lints


def get_clippy_lints():
    if not os.path.isdir("rust-clippy"):
        subprocess.run(["git", "clone", "https://github.com/rust-lang/rust-clippy"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       stdin=subprocess.DEVNULL,
                       cwd=DIR,
                       check=True)
    else:
        subprocess.run(["git", "pull"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       stdin=subprocess.DEVNULL,
                       cwd=os.path.join(DIR, "rust-clippy"),
                       check=True)

    sys.path.insert(0, os.path.join(DIR, "rust-clippy", "util"))
    from lintlib import parse_all

    clippy_lints, _ = parse_all(os.path.join(DIR, "rust-clippy", "clippy_lints", "src"))

    groups = set()
    lints = []
    for lint in clippy_lints:
        lints.append((lint.name, False))
        groups.add(lint.group)
    return lints + [(group, True) for group in groups]


if __name__ == "__main__":
    output = [{"name": l[0], "group": l[1], "rustc": True} for l in get_rustc_lints()] + \
             [{"name": l[0], "group": l[1], "rustc": False} for l in get_clippy_lints()]

    print(json.dumps(output))
