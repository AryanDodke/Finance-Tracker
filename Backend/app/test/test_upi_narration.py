"""Basic tests for the UPI narration parser."""

from app.src.services.upi_narration import parse_upi_narration


def test_upi_debit_merchant():
    narration = "UPI/DR/123456789012/SWIGGY INSTAMART/swiggy@yesbank/Order"
    info = parse_upi_narration(narration)
    assert info.upi_ref == "123456789012"
    assert info.payee_name == "SWIGGY INSTAMART"
    assert info.is_person is False
    assert info.is_self_transfer is False


def test_upi_debit_person():
    narration = "UPI/DR/987654321098/Ramesh Kumar/ramesh@oksbi/Rent"
    info = parse_upi_narration(narration)
    assert info.payee_name == "Ramesh Kumar"
    assert info.is_person is True


def test_neft_is_transfer():
    narration = "NEFT/INWARD/ABC123/Some Bank"
    info = parse_upi_narration(narration)
    assert info.is_self_transfer is True


def test_bill_payment_is_transfer():
    narration = "BIL/BBPS/ELECTRICITY/City Corp"
    info = parse_upi_narration(narration)
    assert info.is_self_transfer is True


def test_unknown_narration():
    narration = "SOME RANDOM NARRATION"
    info = parse_upi_narration(narration)
    assert info.is_self_transfer is False
    assert info.payee_name is None
