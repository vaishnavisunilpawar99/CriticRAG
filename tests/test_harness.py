import os

from agentic_loop_qa.evaluation.harness import run_evaluation

DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "agentic_loop_qa", "data", "sample_dataset.json"
)


def test_run_evaluation_produces_report():
    report = run_evaluation(DATASET_PATH, max_iterations=2)
    assert report.n_examples == 10
    assert 0.0 <= report.baseline_em <= 1.0
    assert 0.0 <= report.loop_em <= 1.0
    assert 0.0 <= report.baseline_f1 <= 1.0
    assert 0.0 <= report.loop_f1 <= 1.0
    assert len(report.per_example) == 10
    assert report.avg_iterations > 0
