from .testset import TestSet, build_test_set, load_or_create_test_set

__all__ = [
    "EvaluationBundle",
    "JudgeVerdict",
    "TestSet",
    "build_test_set",
    "evaluate_pipeline",
    "load_or_create_test_set",
]


def __getattr__(name):
    if name in {"EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"}:
        from . import metrics

        return getattr(metrics, name)
    raise AttributeError(name)
