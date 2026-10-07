"""Small examples of category rules for ordinary files and ZIP members."""

import json
from pathlib import Path

import pytest

from zipsearch.categories import CategoryMatcher, load_categories
from zipsearch.models import Entry
from zipsearch.zip_reader import iter_zip_entries


@pytest.mark.parametrize("filename", [
    "note.txt", "docs/NOTE.TXT", r"C:\docs\note.Txt",
])
def test_extension_matching(filename):
    matcher = CategoryMatcher({"documents": {"extensions": [".TXT"]}})
    assert matcher.match(filename) == ["documents"]


def test_globs_use_only_filename_and_ignore_case():
    matcher = CategoryMatcher({"reports": {"patterns": ["REPORT_?.[ct]sv"]}})
    assert matcher.match("docs/report_a.csv") == ["reports"]
    assert matcher.match("report_a.csv/other.txt") == []
    assert matcher.match("report_ab.csv") == []


def test_extensions_and_patterns_are_alternatives():
    matcher = CategoryMatcher({"code": {"extensions": [".py"],
                                        "patterns": ["requirements*.txt"]}})
    assert matcher.match("main.py") == ["code"]
    assert matcher.match("requirements-dev.txt") == ["code"]
    assert matcher.match("notes.txt") == []


def test_all_matches_in_config_order_without_duplicates():
    matcher = CategoryMatcher({
        "documents": {"extensions": [".txt"], "patterns": ["*.txt"]},
        "reports": {"patterns": ["report_*"]},
    })
    assert matcher.match("report_sales.txt") == ["documents", "reports"]
    assert matcher.match("photo.png") == []


def test_compound_extension_and_extensionless_names():
    matcher = CategoryMatcher({"archives": {"extensions": [".tar.gz"]},
                               "readme": {"patterns": ["README"]}})
    assert matcher.match("backup.TAR.GZ") == ["archives"]
    assert matcher.match("backup.gz") == []
    assert matcher.match("readme") == ["readme"]
    assert matcher.match("notxt") == []


def test_empty_config_and_folder_names():
    assert CategoryMatcher({}).match("anything.txt") == []
    matcher = CategoryMatcher({"all": {"patterns": ["*"]}})
    assert matcher.match("") == []
    assert matcher.match("folder/") == []
    assert matcher.match("folder\\") == []
    assert matcher.match_entry(Entry("a.zip", "docs.txt", 0, False, True)) == []


def test_plain_entry_uses_its_own_path():
    matcher = CategoryMatcher({"documents": {"extensions": [".txt"]}})
    assert matcher.match_entry(Entry("docs/note.txt", "", 5, False)) == [
        "documents"
    ]


def test_zip_entry_uses_inner_name_not_archive_name(make_zip):
    matcher = CategoryMatcher({"documents": {"extensions": [".txt"]},
                               "archives": {"extensions": [".zip"]}})
    path = make_zip({"docs/": "", "docs/a.txt": "hello", "image.png": "x"})
    assert [matcher.match_entry(e) for e in iter_zip_entries(path)] == [
        [], ["documents"], []
    ]


def test_config_is_copied():
    rules = {"documents": {"extensions": [".txt"]}}
    matcher = CategoryMatcher(rules)
    rules["documents"]["extensions"].append(".png")
    assert matcher.match("photo.png") == []


def test_json_config(tmp_path):
    path = tmp_path / "categories.json"
    path.write_text(json.dumps({"documents": {"extensions": [".txt"]}}))
    assert load_categories(path).match("note.txt") == ["documents"]


def test_example_config():
    path = Path(__file__).resolve().parents[1] / "examples/categories.json"
    assert load_categories(path).match("report_october.txt") == [
        "documents", "reports"
    ]


@pytest.mark.parametrize("config", [
    [], {"": {"patterns": ["*"]}}, {"documents": []}, {"documents": {}},
    {"documents": {"extension": [".txt"]}},
    {"documents": {"extensions": ".txt"}},
    {"documents": {"extensions": ["txt"]}},
    {"documents": {"extensions": ["."]}},
    {"documents": {"extensions": ["*.txt"]}},
    {"documents": {"patterns": [""]}},
    {"documents": {"patterns": [12]}},
    {"documents": {"patterns": None}},
])
def test_invalid_rules_have_clear_error(config):
    with pytest.raises(ValueError):
        CategoryMatcher(config)


def test_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{bad json")
    with pytest.raises(ValueError):
        load_categories(path)


def test_missing_json(tmp_path):
    with pytest.raises(OSError):
        load_categories(tmp_path / "missing.json")
