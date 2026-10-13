"""Check the CSV export, reading the file back the way a spreadsheet would."""

import csv

import pytest

from zipsearch.csv_export import COLUMNS, write_results_csv


def make_result(**changes):
    result = {
        "category": ["documents"],
        "filename": "report.txt",
        "folder_location": "docs",
        "zipfile": "",
        "filesizebytes": 120,
        "last_modified": "2020-02-03T04:05:06+00:00",
    }
    result.update(changes)
    return result


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.reader(file))


def test_header_and_row_follow_array_order(tmp_path):
    path = tmp_path / "out.csv"
    write_results_csv([make_result()], path)
    assert read_rows(path) == [
        list(COLUMNS),
        ["documents", "report.txt", "docs", "", "120",
         "2020-02-03T04:05:06+00:00"],
    ]
    assert COLUMNS == ("category", "filename", "folder_location", "zipfile",
                       "filesizebytes", "last_modified")


def test_file_starts_with_utf8_bom(tmp_path):
    path = tmp_path / "out.csv"
    write_results_csv([], path)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_empty_results_write_header_only(tmp_path):
    path = tmp_path / "out.csv"
    write_results_csv([], path)
    assert read_rows(path) == [list(COLUMNS)]


def test_several_categories_share_one_cell(tmp_path):
    path = tmp_path / "out.csv"
    write_results_csv([make_result(category=["documents", "reports"])], path)
    rows = read_rows(path)
    assert len(rows) == 2
    assert rows[1][0] == "documents; reports"


def test_commas_quotes_and_newlines_stay_in_their_cells(tmp_path):
    path = tmp_path / "out.csv"
    name = 'a, "quoted"\nname.txt'
    folder = 'dir, with "quotes"'
    write_results_csv([make_result(filename=name, folder_location=folder)], path)
    rows = read_rows(path)
    assert len(rows) == 2
    assert len(rows[1]) == len(COLUMNS)
    assert rows[1][1] == name
    assert rows[1][2] == folder


def test_non_ascii_text_round_trips(tmp_path):
    path = tmp_path / "out.csv"
    name = "caf\u00e9 \u65e5\u672c\u8a9e \U0001f600.txt"
    write_results_csv([make_result(filename=name)], path)
    assert read_rows(path)[1][1] == name


def test_missing_date_is_an_empty_cell(tmp_path):
    path = tmp_path / "out.csv"
    write_results_csv([make_result(last_modified=None)], path)
    assert read_rows(path)[1][5] == ""


def test_zip_member_row_and_zero_size(tmp_path):
    path = tmp_path / "out.csv"
    write_results_csv(
        [make_result(zipfile="my files.zip", filesizebytes=0)], path)
    row = read_rows(path)[1]
    assert row[3] == "my files.zip"
    assert row[4] == "0"


def test_existing_file_is_replaced(tmp_path):
    path = tmp_path / "out.csv"
    path.write_text("old content that is much longer than the new file " * 20)
    write_results_csv([make_result()], path)
    assert len(read_rows(path)) == 2


def test_accepts_a_generator_and_string_path(tmp_path):
    path = tmp_path / "out.csv"
    write_results_csv((make_result(filename=n) for n in "ab"), str(path))
    assert [row[1] for row in read_rows(path)[1:]] == ["a", "b"]


def test_missing_folder_raises(tmp_path):
    with pytest.raises(OSError):
        write_results_csv([make_result()], tmp_path / "nope" / "out.csv")
