from starter import QuizQuestion, generate_quiz, score_answers

NOTES = """
Photosynthesis converts light energy into chemical energy.
Chlorophyll absorbs light in the chloroplast.
Plants release oxygen as a by-product of photosynthesis.
Cellular respiration releases energy from glucose.
Mitochondria are the main site of cellular respiration.
"""


def test_generate_quiz_respects_count_and_shape():
    quiz = generate_quiz(NOTES, count=3)
    assert len(quiz) == 3
    assert all(isinstance(item, QuizQuestion) for item in quiz)
    assert all(item.question.strip() for item in quiz)
    assert all(item.answer.strip() for item in quiz)


def test_generate_quiz_works_without_network(monkeypatch):
    # The tests must pass offline. A remote call here is a design failure.
    monkeypatch.setenv("LLM_API_KEY", "")
    quiz = generate_quiz(NOTES, count=5)
    assert len(quiz) == 5


def test_score_answers_scores_case_and_whitespace():
    quiz = [
        QuizQuestion("Capital of France?", "Paris"),
        QuizQuestion("2 + 2?", "4"),
        QuizQuestion("Largest planet?", "Jupiter"),
    ]
    result = score_answers(quiz, [" paris ", "4", "Saturn"])
    assert result == {"correct": 2, "total": 3, "percent": 67}


def test_score_answers_handles_missing_answers():
    quiz = [QuizQuestion("A?", "a"), QuizQuestion("B?", "b")]
    result = score_answers(quiz, ["a"])
    assert result["correct"] == 1
    assert result["total"] == 2
    assert result["percent"] == 50


def test_score_answers_handles_empty_quiz():
    assert score_answers([], []) == {"correct": 0, "total": 0, "percent": 0}
