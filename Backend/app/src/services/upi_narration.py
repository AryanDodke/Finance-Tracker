"""
UPI narration parser: splits SBI UPI narration strings into structured fields.
SBI UPI narration patterns:
  UPI/DR/123456789012/PayeeName/upi@handle/Remark
  UPI/CR/123456789012/PayerName/upi@handle/Remark
  IMPS/P2A/...
  BIL/BBPS/...  → Transfer
  NEFT/...      → Transfer
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class UpiInfo:
    payee_name: str | None
    upi_handle: str | None
    upi_ref: str | None
    remark: str | None
    is_person: bool
    is_self_transfer: bool


# Patterns that indicate self-transfer or bill payment
_TRANSFER_PREFIXES = {
    "NEFT", "RTGS", "IMPS/P2M", "BIL", "BBPS", "SWP", "CLG", "ATM",
}

# Tokens that suggest a merchant (not a person)
_MERCHANT_TOKENS = {
    "swiggy", "zomato", "amazon", "flipkart", "uber", "ola", "netflix",
    "spotify", "hotstar", "paytm", "phonepe", "gpay", "razorpay", "stripe",
    "jio", "airtel", "bsnl", "vodafone", "dth", "electricity", "gas",
    "insurance", "hospital", "clinic", "pharmacy", "supermarket", "mart",
    "store", "shop", "pvt", "ltd", "llp", "corp", "technologies", "tech",
    "solutions", "services", "foods", "restaurant", "cafe", "hotel",
}

# UPI handle suffixes that suggest a merchant/business
_BUSINESS_HANDLES = {
    "@yesbank", "@axisbank", "@icici", "@hdfcbank", "@kotak", "@sbi",
    "@paytm", "@razorpay", "@cashfree", "@easebuzz", "@billdesk",
    "@upi", "@zomato", "@swiggy", "@uber",
}


def looks_like_person(name: str, handle: str | None) -> bool:
    """True if the payee looks like an individual, not a business."""
    if not name:
        return False
    name_lower = name.lower()

    # Business token match → not a person
    for token in _MERCHANT_TOKENS:
        if token in name_lower:
            return False

    if handle:
        handle_lower = handle.lower()
        for bh in _BUSINESS_HANDLES:
            if handle_lower.endswith(bh):
                return False
        # Personal handles: @oksbi, @okaxis, @ybl, @ibl, @apl, @wayfarer
        personal_suffixes = {"@oksbi", "@okaxis", "@ybl", "@ibl", "@apl", "@okhdfcbank", "@okicici"}
        for ps in personal_suffixes:
            if handle_lower.endswith(ps):
                return True

    # Name looks like a person: 2-3 words, no digits
    words = name_lower.split()
    if 1 <= len(words) <= 3 and all(w.isalpha() for w in words):
        return True

    return False


# Main SBI UPI pattern: UPI/DR/REFNO/NAME/HANDLE/REMARK
_UPI_RE = re.compile(
    r"^UPI[/-](?P<dir>DR|CR)[/-]"
    r"(?P<ref>\d+)[/-]"
    r"(?P<name>[^/]+)[/-]"
    r"(?P<handle>[^/]*)[/-]?"
    r"(?P<remark>.*)$",
    re.IGNORECASE,
)

# IMPS pattern
_IMPS_RE = re.compile(
    r"^IMPS[/-](?P<ref>\d+)[/-](?P<name>[^/]+)(?:[/-](?P<handle>[^/]*))?",
    re.IGNORECASE,
)


def parse_upi_narration(narration: str) -> UpiInfo:
    """Parse an SBI narration string into structured UpiInfo."""
    narration = narration.strip()

    # Check for self-transfer / bill payment
    upper = narration.upper()
    for prefix in _TRANSFER_PREFIXES:
        if upper.startswith(prefix):
            return UpiInfo(
                payee_name=None,
                upi_handle=None,
                upi_ref=None,
                remark=narration,
                is_person=False,
                is_self_transfer=True,
            )

    # Try UPI pattern
    m = _UPI_RE.match(narration)
    if m:
        name = m.group("name").strip()
        handle = m.group("handle").strip() or None
        ref = m.group("ref").strip()
        remark = m.group("remark").strip() or None
        is_person = looks_like_person(name, handle)
        return UpiInfo(
            payee_name=name or None,
            upi_handle=handle,
            upi_ref=ref,
            remark=remark,
            is_person=is_person,
            is_self_transfer=False,
        )

    # Try IMPS pattern
    m = _IMPS_RE.match(narration)
    if m:
        name = m.group("name").strip()
        handle = m.group("handle") and m.group("handle").strip() or None
        ref = m.group("ref").strip()
        is_person = looks_like_person(name, handle)
        return UpiInfo(
            payee_name=name or None,
            upi_handle=handle,
            upi_ref=ref,
            remark=None,
            is_person=is_person,
            is_self_transfer=False,
        )

    # Unknown format
    return UpiInfo(
        payee_name=None,
        upi_handle=None,
        upi_ref=None,
        remark=narration,
        is_person=False,
        is_self_transfer=False,
    )
