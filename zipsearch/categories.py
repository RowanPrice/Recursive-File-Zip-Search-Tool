"""Match file names to categories without opening files or changing the CLI."""

import json
from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import List, Mapping, Sequence

from zipsearch.models import Entry, Path

CategoryConfig = Mapping[str, Mapping[str, Sequence[str]]]


class CategoryMatcher:
    """Use a small dict: category -> extensions and/or filename patterns.

    Rules use OR: an extension OR a pattern is enough to match a category.
    Names and rules are case-insensitive. Patterns are shell-style globs:
    '*' means any text, '?' one character, and '[ab]' either a or b.
    Match only the final filename, not its parent folders. Return every
    matching category in config order, or [] when nothing matches.
    """

    def __init__(self, categories: CategoryConfig) -> None:
        """Validate and copy rules so later edits cannot change this matcher."""
        if not isinstance(categories, Mapping):
            raise ValueError("Categories must be a dict of category rules")
        self._rules = []
        for category, rules in categories.items():
            if not isinstance(category, str) or not category.strip():
                raise ValueError("Each category must have a non-empty name")
            if not isinstance(rules, Mapping):
                raise ValueError("Rules for {!r} must be a dict".format(category))
            if set(rules) - {"extensions", "patterns"}:
                raise ValueError("Unknown rule field in {!r}".format(category))
            extensions = self._strings(rules, "extensions", category)
            patterns = self._strings(rules, "patterns", category)
            if not extensions and not patterns:
                raise ValueError("Category {!r} has no rules".format(category))
            for extension in extensions:
                if not extension.startswith(".") or extension == ".":
                    raise ValueError("Extensions must start with '.', e.g. .txt")
                if any(char in extension for char in "/\\*?[]"):
                    raise ValueError("Extensions cannot contain paths or globs")
            self._rules.append((category, extensions, patterns))

    @staticmethod
    def _strings(rules, key, category):
        """Require a list/tuple of non-empty strings, not a single string."""
        values = rules.get(key, [])
        if not isinstance(values, (list, tuple)) or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError(
                "{} for {!r} must be a list of non-empty strings".format(
                    key, category
                )
            )
        return tuple(value.lower() for value in values)

    def match(self, filename: str) -> List[str]:
        """Return category names for a normal path or a ZIP member name.

        No file needs to exist: this only checks its name. Both '/' and '\\'
        are accepted as path separators. A trailing separator means a folder.
        Compound extensions such as '.tar.gz' work too.
        """
        path = filename.replace("\\", "/")
        if not path or path.endswith("/"):
            return []
        name = PurePosixPath(path).name.lower()
        return [
            category for category, extensions, patterns in self._rules
            if any(name.endswith(extension) for extension in extensions)
            or any(fnmatchcase(name, pattern) for pattern in patterns)
        ]

    def match_entry(self, entry: Entry) -> List[str]:
        """Check the member's name inside a ZIP, or a plain file's own path.

        Directories never match, even if their name ends in '.txt'. This does
        not open the archive or read the entry's contents.
        """
        if entry.is_dir:
            return []
        return self.match(entry.inner_path or entry.container_path)


def load_categories(path: Path) -> CategoryMatcher:
    """Read a UTF-8 JSON config and build the same matcher used with a dict.

    Bad JSON/rules raise ValueError. Missing or unreadable files raise OSError.
    """
    with open(path, encoding="utf-8") as config_file:
        return CategoryMatcher(json.load(config_file))
