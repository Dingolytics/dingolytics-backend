import datetime
from unittest import TestCase, skipIf

from mock import MagicMock

from redash.query_runner import TYPE_DATETIME, TYPE_FLOAT
from redash.query_runner.google_spreadsheets import (
    TYPE_BOOLEAN,
    TYPE_STRING,
    _get_columns_and_column_names,
    _value_eval_list,
    is_url_key,
    parse_query,
)
from redash.query_runner.google_spreadsheets import (
    WorksheetNotFoundError,
    parse_spreadsheet,
    parse_worksheet,
)


class TestValueEvalList(TestCase):
    def test_handles_unicode(self):
        values = ["יוניקוד", "test", "value"]
        self.assertEqual(values, _value_eval_list(values, [TYPE_STRING] * len(values)))

    def test_handles_boolean(self):
        values = ["true", "false", "True", "False", "TRUE", "FALSE"]
        converted_values = [True, False, True, False, True, False]
        self.assertEqual(
            converted_values, _value_eval_list(values, [TYPE_BOOLEAN] * len(values))
        )

    def test_handles_empty_values(self):
        values = ["", None]
        converted_values = [None, None]
        self.assertEqual(
            converted_values, _value_eval_list(values, [TYPE_STRING, TYPE_STRING])
        )

    def test_handles_float(self):
        values = ["3.14", "-273.15"]
        converted_values = [3.14, -273.15]
        self.assertEqual(
            converted_values, _value_eval_list(values, [TYPE_FLOAT, TYPE_FLOAT])
        )

    def test_handles_datetime(self):
        values = ["2018-06-28", "2020-2-29"]
        converted_values = [
            datetime.datetime(2018, 6, 28, 0, 0),
            datetime.datetime(2020, 2, 29, 0, 0),
        ]
        self.assertEqual(
            converted_values, _value_eval_list(values, [TYPE_DATETIME, TYPE_DATETIME])
        )


class TestParseSpreadsheet(TestCase):
    def test_returns_meaningful_error_for_missing_worksheet(self):
        spreadsheet = MagicMock()

        spreadsheet.worksheets = MagicMock(return_value=[])
        self.assertRaises(WorksheetNotFoundError, parse_spreadsheet, spreadsheet, 0)

        spreadsheet.worksheets = MagicMock(return_value=[1, 2])
        self.assertRaises(WorksheetNotFoundError, parse_spreadsheet, spreadsheet, 2)


empty_worksheet = []
only_headers_worksheet = [["Column A", "Column B"]]
regular_worksheet = [
    ["String Column", "Boolean Column", "Number Column"],
    ["A", "TRUE", "1"],
    ["B", "FALSE", "2"],
    ["C", "TRUE", "3"],
    ["D", "FALSE", "4"],
]


# The following test that the parse function doesn't crash. They don't test correct output.
class TestParseWorksheet(TestCase):
    def test_parse_empty_worksheet(self):
        parse_worksheet(empty_worksheet)

    def test_parse_only_headers_worksheet(self):
        parse_worksheet(only_headers_worksheet)

    def test_parse_regular_worksheet(self):
        parse_worksheet(regular_worksheet)

    def test_parse_worksheet_with_duplicate_column_names(self):
        worksheet = [
            ["Column", "Another Column", "Column"],
            ["A", "TRUE", "1"],
            ["B", "FALSE", "2"],
            ["C", "TRUE", "3"],
            ["D", "FALSE", "4"],
        ]
        parsed = parse_worksheet(worksheet)

        columns = [column["name"] for column in parsed["columns"]]
        self.assertEqual("Column", columns[0])
        self.assertEqual("Another Column", columns[1])
        self.assertEqual("Column1", columns[2])

        self.assertEqual("A", parsed["rows"][0]["Column"])
        self.assertEqual(True, parsed["rows"][0]["Another Column"])
        self.assertEqual(1, parsed["rows"][0]["Column1"])


class TestParseQuery(TestCase):
    def test_parse_query(self):
        parsed = parse_query("key|0")
        self.assertEqual(("key", 0), parsed)


class TestGetColumnsAndColumnNames(TestCase):
    def test_get_columns(self):
        _columns = ["foo", "bar", "baz"]
        columns, column_names = _get_columns_and_column_names(_columns)

        self.assertEqual(_columns, column_names)

    def test_get_columns_with_duplicated(self):
        _columns = ["foo", "bar", "baz", "foo", "baz"]
        columns, column_names = _get_columns_and_column_names(_columns)

        self.assertEqual(["foo", "bar", "baz", "foo1", "baz2"], column_names)


    def test_get_columns_with_blank(self):
        _columns = ["foo", "", "baz", ""]
        columns, column_names = _get_columns_and_column_names(_columns)

        self.assertEqual(["foo", "column_B", "baz", "column_D"], column_names)


class TestIsUrlKey(TestCase):
    def test_is_url_key(self):
        _key = "https://docs.google.com/spreadsheets/d/key/edit#gid=12345678"
        self.assertTrue(is_url_key(_key))

        _key = "key|0"
        self.assertFalse(is_url_key(_key))
