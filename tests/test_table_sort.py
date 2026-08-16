"""Tests for TableSortMixin's pure sort-key helpers.

_normalize_for_sort and _make_sort_key don't touch self.table/self.model or
any other collaborator the mixin's docstring lists as required, so they can
be exercised directly on a bare TableSortMixin() instance without a real
QApplication or a populated view.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

from features.members.table_sort import TableSortMixin


@pytest.fixture()
def mixin() -> TableSortMixin:
    return TableSortMixin()


class _FakeHeader:
    def __init__(self) -> None:
        self.indicator_shown = False

    def setSortIndicator(self, column, order) -> None:
        pass

    def setSortIndicatorShown(self, shown: bool) -> None:
        self.indicator_shown = shown


class _FakeTable:
    def __init__(self) -> None:
        self._header = _FakeHeader()

    def horizontalHeader(self):
        return self._header

    def clearSelection(self) -> None:
        pass


class TestNormalizeForSort:
    def test_none_returns_empty_string(self, mixin):
        assert mixin._normalize_for_sort(None) == ""

    def test_strips_accents(self, mixin):
        assert mixin._normalize_for_sort("Álvaro") == "alvaro"
        assert mixin._normalize_for_sort("Muñoz") == "munoz"

    def test_casefolds(self, mixin):
        assert mixin._normalize_for_sort("HELLO") == "hello"

    def test_strips_surrounding_whitespace(self, mixin):
        assert mixin._normalize_for_sort("  Hello  ") == "hello"

    def test_accented_and_plain_forms_are_equal(self, mixin):
        assert mixin._normalize_for_sort("Álvaro") == mixin._normalize_for_sort("Alvaro")

    def test_non_string_input_is_stringified(self, mixin):
        assert mixin._normalize_for_sort(123) == "123"


class TestMakeSortKey:
    def test_none_sorts_as_empty_text(self, mixin):
        assert mixin._make_sort_key(None) == (1, "")

    def test_integer_like_string_is_numeric(self, mixin):
        assert mixin._make_sort_key("42") == (0, 42)

    def test_float_like_string_is_numeric(self, mixin):
        assert mixin._make_sort_key("3.14") == (0, 3.14)

    def test_numeric_string_with_whitespace_is_numeric(self, mixin):
        assert mixin._make_sort_key(" 10 ") == (0, 10)

    def test_text_falls_back_to_normalized_text(self, mixin):
        assert mixin._make_sort_key("Álvaro") == (1, "alvaro")

    def test_numeric_keys_sort_before_text_keys(self, mixin):
        assert mixin._make_sort_key("2") < mixin._make_sort_key("abc")

    def test_full_sort_orders_numbers_before_accent_normalized_text(self, mixin):
        raw = ["abc", "10", "Álvaro", "2"]
        assert sorted(raw, key=mixin._make_sort_key) == ["2", "10", "abc", "Álvaro"]


class TestApplySortKeepsCellsNonEditable:
    """Regression test: _apply_sort rebuilds the model with fresh
    QStandardItems on every header click, and used to skip setEditable(False)
    on them - so a cell that was locked read-only on initial load (see
    menu_service.py's _populate_model) would silently become editable again
    (double-click to edit) the moment the user sorted by clicking a header.
    """

    def _make_view(self, rows) -> TableSortMixin:
        view = TableSortMixin()
        view.table = _FakeTable()
        view.model = QStandardItemModel(0, len(rows[0]))
        for row in rows:
            items = [QStandardItem(v) for v in row]
            for item in items:
                item.setEditable(False)
            view.model.appendRow(items)
        view.ensure_columns_fill = lambda: None
        view._sort_column = None
        view._sort_order = None
        return view

    def test_sorted_cells_remain_non_editable(self):
        view = self._make_view([["Beatriz", "2"], ["Ana", "1"]])
        view._sort_column = 0
        view._sort_order = Qt.SortOrder.AscendingOrder

        view._apply_sort()

        assert view.model.rowCount() == 2
        for r in range(view.model.rowCount()):
            for c in range(view.model.columnCount()):
                assert view.model.item(r, c).isEditable() is False

    def test_sort_actually_reorders_rows(self):
        view = self._make_view([["Beatriz", "2"], ["Ana", "1"]])
        view._sort_column = 0
        view._sort_order = Qt.SortOrder.AscendingOrder

        view._apply_sort()

        assert view.model.item(0, 0).text() == "Ana"
        assert view.model.item(1, 0).text() == "Beatriz"
