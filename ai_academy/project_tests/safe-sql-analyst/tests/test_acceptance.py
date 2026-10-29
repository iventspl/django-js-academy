from starter import enforce_limit, validate_sql


def test_simple_select_is_allowed():
    assert validate_sql("SELECT id, name FROM customers") is True


def test_trailing_semicolon_is_allowed():
    assert validate_sql("SELECT count(*) FROM orders;") is True


def test_writes_are_rejected():
    for sql in (
        "DELETE FROM customers",
        "UPDATE customers SET name = 'x'",
        "DROP TABLE orders",
        "INSERT INTO orders VALUES (1)",
    ):
        assert validate_sql(sql) is False, sql


def test_stacked_statements_and_comments_are_rejected():
    assert validate_sql("SELECT 1; DROP TABLE users") is False
    assert validate_sql("SELECT * FROM users -- ignore") is False
    assert validate_sql("") is False


def test_limit_is_added_once():
    sql = enforce_limit("SELECT * FROM orders", limit=50)
    assert sql.endswith("LIMIT 50")
    existing = "SELECT * FROM orders LIMIT 10"
    assert enforce_limit(existing, limit=50) == existing


def test_limit_is_case_insensitive():
    existing = "SELECT * FROM orders limit 10"
    assert enforce_limit(existing, limit=50) == existing
