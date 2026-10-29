from starter import Chunk, answer_with_citations, chunk_document, retrieve, validate_citations

TEXT = (
    "Refunds are available within 30 days of purchase. "
    "Contact support with the order id. "
    "Enterprise plans include a dedicated success manager. "
    "Invoices are available in the billing settings. "
    "Security incidents must be reported within 24 hours. "
    "The status page lists current incidents."
)


def test_chunks_cover_the_document():
    chunks = chunk_document(TEXT, "handbook", size=80, overlap=20)
    assert len(chunks) >= 2
    assert chunks[-1].text[-20:] == TEXT[-20:]
    assert all(chunk.source == "handbook" for chunk in chunks)


def test_retrieve_finds_relevant_chunk():
    chunks = chunk_document(TEXT, "handbook", size=80, overlap=10)
    results = retrieve("How many days do I have for a refund?", chunks, k=2)
    assert any("30 days" in chunk.text for chunk in results)


def test_validate_citations_rejects_fabricated_numbers():
    chunks = [Chunk("a", "doc", 0), Chunk("b", "doc", 1)]
    assert validate_citations([0, 1], chunks) is True
    assert validate_citations([0, 9], chunks) is False


def test_answer_abstains_when_no_evidence_is_relevant():
    chunks = chunk_document("Office hours are 9 to 5.", "policy", size=50, overlap=0)
    result = answer_with_citations("What is the refund policy?", chunks)
    assert result["citations"] == []
    assert result["answer"].strip() == "" or "don't know" in result["answer"].lower()


def test_answer_returns_valid_citations_when_evidence_exists():
    chunks = chunk_document(TEXT, "handbook", size=80, overlap=10)
    result = answer_with_citations("What is the refund window?", chunks)
    assert result["answer"].strip()
    assert validate_citations(result["citations"], chunks)
