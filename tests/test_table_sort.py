"""Tests for TableSortMixin's pure sort-key helpers.

_normalize_for_sort and _make_sort_key don't touch self.table/self.model or
any other collaborator the mixin's docstring lists as required, so they can
be exercised directly on a bare TableSortMixin() instance without a real
QApplication or a populated view.
"""

from __future__ import annotations

import pytest

from features.members.table_sort import TableSortMixin


@pytest.fixture()
def mixin() -> TableSortMixin:
    return TableSortMixin()


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
