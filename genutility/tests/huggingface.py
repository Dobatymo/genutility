import sys
import unittest

import numpy as np

from genutility.test import MyTestCase


@unittest.skipIf(sys.flags.optimize == 2, "evaluate doesn't work with optimize=2")
class HuggingfaceTest(MyTestCase):
    def test_binary(self):
        from genutility.huggingface import Accuracy

        accuracy = Accuracy()

        with self.assertRaises(ValueError):
            predictions = np.array([[0, 0, 1], [0, 0, 1]])
            references = np.array([[0, 0, 0], [0, 0, 1]])
            accuracy.compute(predictions=predictions, references=references)

        predictions = np.array([0, 1])
        references = np.array([0, 0])

        truth = {"accuracy": 0.5}
        result = accuracy.compute(predictions=predictions, references=references)
        self.assertEqual(truth, result)
        result = accuracy.compute(predictions=predictions, references=references, average="binary")
        self.assertEqual(truth, result)

    def test_multilabel(self):
        from genutility.huggingface import Accuracy

        accuracy = Accuracy(config_name="multilabel")

        with self.assertRaises(ValueError):
            predictions = np.array([0, 1])
            references = np.array([0, 0])
            accuracy.compute(predictions=predictions, references=references)

        predictions = np.array([[0, 0, 1], [0, 0, 1]])
        references = np.array([[0, 0, 0], [0, 0, 1]])

        truth = {"accuracy": 0.5}
        result = accuracy.compute(predictions=predictions, references=references)
        self.assertEqual(truth, result)
        result = accuracy.compute(predictions=predictions, references=references, average="binary")
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
