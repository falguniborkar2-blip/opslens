from opslens.eval.metrics import average_precision_at_k, dedupe, recall_at_k, reciprocal_rank


def test_metrics() -> None:
    ranked = ["a", "b", "c"]
    assert recall_at_k(ranked, {"b", "z"}, 2) == 0.5
    assert reciprocal_rank(ranked, {"c"}) == 1 / 3
    assert reciprocal_rank(ranked, {"z"}) == 0.0
    # relevant at ranks 1 and 3 -> (1/1 + 2/3) / 2
    assert abs(average_precision_at_k(ranked, {"a", "c"}, 3) - (1 + 2 / 3) / 2) < 1e-9
    assert dedupe(["a", "a", "b", "a"]) == ["a", "b"]
