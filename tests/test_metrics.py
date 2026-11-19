from agentic_loop_qa.evaluation.metrics import exact_match, f1_score, normalize_answer


def test_normalize_answer_strips_articles_and_punctuation():
    assert normalize_answer("The Eiffel Tower.") == "eiffel tower"
    assert normalize_answer("A cat!") == "cat"


def test_exact_match_exact_and_normalized():
    assert exact_match("Gustave Eiffel", ["Gustave Eiffel"]) == 1.0
    assert exact_match("the gustave eiffel", ["Gustave Eiffel"]) == 1.0
    assert exact_match("Isaac Newton", ["Gustave Eiffel"]) == 0.0


def test_exact_match_multiple_gold_answers():
    assert exact_match("Everest", ["Mount Everest", "Everest"]) == 1.0


def test_f1_partial_overlap():
    score = f1_score("Mount Everest mountain", ["Mount Everest"])
    assert 0.0 < score < 1.0


def test_f1_perfect_and_zero():
    assert f1_score("Mount Everest", ["Mount Everest"]) == 1.0
    assert f1_score("banana", ["Mount Everest"]) == 0.0


def test_f1_empty_prediction():
    assert f1_score("", ["Mount Everest"]) == 0.0
