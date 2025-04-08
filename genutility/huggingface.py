from typing import Any

import datasets
import evaluate
from sklearn.metrics import accuracy_score


class Accuracy(evaluate.Metric):
    def _info(self):
        return evaluate.MetricInfo(
            description="Binary, multi-class or Multi-label accuracy",
            citation="",
            inputs_description="A dataset with `predictions` and `references` columns",
            features=datasets.Features(
                {
                    "predictions": datasets.Sequence(datasets.Value("int32")),
                    "references": datasets.Sequence(datasets.Value("int32")),
                }
                if self.config_name == "multilabel"
                else {
                    "predictions": datasets.Value("int32"),
                    "references": datasets.Value("int32"),
                }
            ),
            reference_urls=["https://scikit-learn.org/stable/modules/generated/sklearn.metrics.accuracy_score.html"],
        )

    def _compute(self, predictions, references, normalize=True, sample_weight=None, average: Any = None):
        """average is ignored"""

        return {
            "accuracy": float(accuracy_score(references, predictions, normalize=normalize, sample_weight=sample_weight))
        }
