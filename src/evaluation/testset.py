from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json


@dataclass(frozen=True)
class TestSet:
    samples: list[dict[str, Any]]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build the fixed five-question benchmark required by checkpoint 2."""
    if len(df) < 5:
        raise ValueError("At least 5 clean documents are required to build the benchmark.")

    selected = df.sort_values(["published", "paper_id"], ascending=[False, True]).head(5).reset_index(drop=True)
    question_types = ["summary", "authors", "date", "category"]
    questions: list[dict[str, Any]] = []
    for index, (question_type, (_, row)) in enumerate(zip(question_types, selected.head(4).iterrows(), strict=True), start=1):
        title = str(row["title"])
        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))
        elif question_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = str(row["authors_joined"])
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row["published"])
        else:  # category
            question = f"What categories describe the paper '{title}'?"
            ground_truth = str(row["categories_joined"])
        questions.append(
            {
                "id": f"eval_{index:03d}",
                "type": question_type,
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    first = selected.iloc[0]
    second = selected.iloc[4]
    questions.append(
        {
            "id": "eval_005",
            "type": "multi_hop",
            "question_type": "multi_hop",
            "question": (
                f"Compare the research areas of '{first['title']}' and '{second['title']}'. "
                "Which categories are associated with each paper?"
            ),
            "ground_truth": (
                f"{first['title']}: {first['categories_joined']}; "
                f"{second['title']}: {second['categories_joined']}"
            ),
            "ground_truth_doc_ids": [str(first["paper_id"]), str(second["paper_id"])],
        }
    )

    write_json(output_path, questions)
    return questions


def load_or_create_test_set(df: pd.DataFrame, output_path, refresh: bool = False) -> TestSet:
    """Load the stable benchmark or create it once from the clean dataset."""
    if not refresh and output_path.exists():
        samples = read_json(output_path)
    else:
        samples = build_test_set(df, output_path)
    return TestSet(samples=samples)
