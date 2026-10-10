"""Tests for the notes parser."""
from decimal import Decimal

from app.src.services.notes_parser import regex_parse_notes

SAMPLE_NOTES = """
Personal:
  Rent - 12000
  Food - 8500

Travel:
  Train - 2000
  Auto - 500

Home Expense:
  Electricity - 1500
  Internet - 800

Outing:
  Dinner - 2500
"""


def test_regex_parse_standard_format():
    lines = regex_parse_notes(SAMPLE_NOTES)
    assert len(lines) == 8

    rent = next((l for l in lines if l.item_text == "Rent"), None)
    assert rent is not None
    assert rent.amount == Decimal("12000")
    assert rent.category == "Personal"


def test_regex_parse_travel():
    lines = regex_parse_notes(SAMPLE_NOTES)
    train = next((l for l in lines if l.item_text == "Train"), None)
    assert train is not None
    assert train.amount == Decimal("2000")
    assert train.category == "Travel"


def test_empty_text():
    lines = regex_parse_notes("")
    assert lines == []


def test_no_amounts():
    lines = regex_parse_notes("Just some text without numbers")
    assert lines == []
