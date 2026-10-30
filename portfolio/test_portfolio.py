import importlib.util
from pathlib import Path
import tempfile
import unittest
import pandas as pd

spec = importlib.util.spec_from_file_location('review_workflow', Path(__file__).with_name('review_workflow.py'))
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class EvaluationTests(unittest.TestCase):
    def test_common_pii_is_masked(self):
        self.assertEqual(workflow.redact('email a@b.com telefone +55 11 99999-8888'), 'email [REDACTED] telefone [REDACTED]')

    def test_strict_coverage_and_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            gold = pd.DataFrame({'sample_id':['R1','R2'], 'human_label':['positive','delivery_delay'], 'privacy_checked':['yes','yes'], 'annotator':['tester','tester']})
            pred = pd.DataFrame({'sample_id':['R2','R1'], 'predicted_label':['positive','positive'], 'needs_review':[True, False]})
            gold.to_csv(d/'gold.csv', index=False); pred.to_csv(d/'pred.csv', index=False)
            result = workflow.evaluate(d/'gold.csv', d/'pred.csv', d/'result.json')
            self.assertEqual(result['accuracy'], .5)
            self.assertEqual(result['manual_review_share'], .5)
            pred.iloc[:1].to_csv(d/'pred.csv', index=False)
            with self.assertRaises(ValueError): workflow.evaluate(d/'gold.csv', d/'pred.csv', d/'result.json')

    def test_order_grain_differs_from_item_weighting(self):
        orders = pd.DataFrame({'order_id':['a','b'], 'review_score':[1,5]})
        items = pd.DataFrame({'order_id':['a','a','b'], 'seller_id':['x','x','x']})
        selected = orders[orders.order_id.isin(items.order_id.unique())]
        self.assertEqual(selected.review_score.mean(), 3)
        self.assertNotEqual(items.merge(orders).review_score.mean(), 3)


if __name__ == '__main__': unittest.main()
