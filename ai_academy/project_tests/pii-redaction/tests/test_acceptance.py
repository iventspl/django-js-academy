from starter import redact


def test_email_is_redacted():
    text, counts = redact("Contact ala@example.com for details.")
    assert "[EMAIL]" in text
    assert "ala@example.com" not in text
    assert counts["email"] == 1


def test_phone_number_is_redacted():
    text, counts = redact("Call +48 123 456 789 tomorrow.")
    assert "[PHONE]" in text
    assert counts["phone"] == 1


def test_card_like_number_is_redacted():
    text, counts = redact("Card 4111 1111 1111 1111 was declined.")
    assert "[CARD]" in text
    assert counts["card"] == 1


def test_ordinary_numbers_are_preserved():
    text, counts = redact("Order 1234 shipped in 2026.")
    assert "1234" in text
    assert "2026" in text
    assert counts == {"email": 0, "phone": 0, "card": 0}


def test_multiple_identifiers_are_counted():
    text, counts = redact("a@b.com called 123 456 789 and used 4111111111111111.")
    assert counts["email"] >= 1
    assert counts["phone"] >= 1
    assert counts["card"] >= 1
