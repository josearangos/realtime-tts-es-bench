"""Replace absolute filesystem paths in text (FR-010). Standard library only."""

from __future__ import annotations

import re

# An absolute POSIX path: starts at a "/" that is not part of a URL ("://"), a relative
# "./x" or a word like "and/or".
_PATH = re.compile(r"(?<![\w/:.])/[^\s'\"`,;)\]>]+")


def scrub_paths(text: str, extra: tuple[str, ...] = ()) -> str:
    for known in sorted((e for e in extra if e), key=len, reverse=True):
        text = text.replace(known, "<path>")
    return _PATH.sub("<path>", text)
