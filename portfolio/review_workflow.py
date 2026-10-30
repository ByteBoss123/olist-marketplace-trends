"""Local review sampling, privacy triage, and strict evaluation of imported predictions.

No API calls. Regex screening is NOT a guarantee that text contains no personal data.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import pandas as pd

LABELS = {'delivery_delay', 'wrong_or_missing_item', 'damage_or_quality', 'positive', 'other', 'unclear'}


def redact(text):
    text = str(text)
    patterns = [r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', r'https?://\S+',
                r'(?<!\w)(?:\+?\d[\d ()\-.]{6,}\d)(?!\w)']
    for pattern in patterns:
        text = re.sub(pattern, '[REDACTED]', text)
    return text


def sample(source, output, size=150):
    rows = pd.read_csv(source).sort_values(['review_answer_timestamp', 'review_id', 'review_score'], na_position='first')
    rows = rows.drop_duplicates('order_id', keep='last')
    rows = rows[rows.review_comment_message.fillna('').str.strip().ne('')]
    rows = rows.sample(n=min(size, len(rows)), random_state=20261030)
    out = pd.DataFrame({'sample_id': [f'R{i:04}' for i in range(1, len(rows)+1)],
                        'review_text': rows.review_comment_message.map(redact).to_list()})
    for col in ['privacy_checked', 'human_label', 'annotator', 'notes']:
        out[col] = ''
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)
    print(f'{len(out)} LOCAL samples written; review privacy and Portuguese meaning before external use.')


def evaluate(gold_path, prediction_path, output):
    gold, pred = pd.read_csv(gold_path).fillna(''), pd.read_csv(prediction_path).fillna('')
    for name, frame in [('gold', gold), ('predictions', pred)]:
        if not frame.sample_id.is_unique or frame.sample_id.eq('').any():
            raise ValueError(f'{name}: sample IDs must be unique and nonempty')
    if set(gold.sample_id) != set(pred.sample_id):
        raise ValueError('Predictions must match every gold sample ID exactly')
    if not gold.human_label.isin(LABELS).all() or not pred.predicted_label.isin(LABELS).all():
        raise ValueError('Invalid or incomplete labels')
    if not gold.privacy_checked.astype(str).str.lower().eq('yes').all():
        raise ValueError('Human privacy review is incomplete')
    if gold.annotator.astype(str).str.strip().eq('').any():
        raise ValueError('Record the human annotator')
    if 'needs_review' not in pred or not pred.needs_review.astype(str).str.lower().isin(['true','false']).all():
        raise ValueError('Every prediction needs a true/false needs_review flag')
    joined = gold.merge(pred, on='sample_id', validate='one_to_one')
    report = {'n': len(joined), 'accuracy': float(joined.human_label.eq(joined.predicted_label).mean()),
              'manual_review_share': float(joined.needs_review.astype(str).str.lower().eq('true').mean()),
              'per_class': {}, 'source_hashes': {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [gold_path, prediction_path]}}
    f1s = []
    for label in sorted(LABELS):
        truth, guess = joined.human_label.eq(label), joined.predicted_label.eq(label)
        tp = int((truth & guess).sum())
        precision = tp / guess.sum() if guess.sum() else 0.0
        recall = tp / truth.sum() if truth.sum() else 0.0
        f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
        report['per_class'][label] = dict(support=int(truth.sum()), precision=float(precision), recall=float(recall), f1=float(f1))
        if truth.any() or guess.any(): f1s.append(f1)
    report['macro_f1_present_classes'] = sum(f1s)/len(f1s) if f1s else None
    report['confusion_matrix'] = pd.crosstab(joined.human_label, joined.predicted_label).to_dict()
    Path(output).write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='action', required=True)
    s = sub.add_parser('sample'); s.add_argument('source'); s.add_argument('output'); s.add_argument('--size', type=int, default=150)
    e = sub.add_parser('evaluate'); e.add_argument('gold'); e.add_argument('predictions'); e.add_argument('output')
    a = p.parse_args()
    if a.action == 'sample': sample(a.source, a.output, a.size)
    else: print(json.dumps(evaluate(a.gold, a.predictions, a.output), indent=2))
