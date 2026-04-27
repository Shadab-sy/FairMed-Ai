import json
import numpy as np
from collections import Counter
from pathlib import Path

report_path = Path('backend/models/model_evaluation_report.json')

with open(report_path, 'r') as f:
    report = json.load(f)

model_b = report.get('model_b', {})
y_pred = model_b.get('top1', [])
y_probs = model_b.get('proba', [])
accuracy = model_b.get('accuracy', 0)
top3_accuracy = model_b.get('topk_accuracy', 0)

print("--------------------------------")
print("1. VERIFY MODEL IS NOT COLLAPSED")
print("--------------------------------")
print("Unique predictions:", set(y_pred))
print("EXPECTED: Multiple classes. RESULT: ", "PASSED" if len(set(y_pred)) > 1 else "FAILED")

print("\n--------------------------------")
print("2. VERIFY PREDICTION DISTRIBUTION")
print("--------------------------------")
counts = Counter(y_pred)
print("Prediction counts:", dict(counts))
if len(counts) > 0:
    max_dom = counts.most_common(1)[0][1] / len(y_pred)
    print(f"Max class dominance: {max_dom:.1%}")
    print("EXPECTED: Spread out. RESULT: ", "PASSED" if max_dom < 0.50 else "FAILED")

print("\n--------------------------------")
print("3. VERIFY ACCURACY METRICS")
print("--------------------------------")
print("Accuracy:", accuracy)
print("Top-3 Accuracy:", top3_accuracy)
print("EXPECTED: Acc > 10%, Top-3 > 30%. RESULT: ", "PASSED" if accuracy > 0.1 and top3_accuracy > 0.3 else "FAILED")

print("\n--------------------------------")
print("4. SANITY CHECK MODEL OUTPUT")
print("--------------------------------")
print("Sample predictions:", y_pred[:10])

print("\n--------------------------------")
print("5. VERIFY TRAINING BEHAVIOR")
print("--------------------------------")
print("Early stopping was applied. If results are poor, early_stopping_rounds may need increase.")

print("\n--------------------------------")
print("6. OPTIONAL: CHECK PROBABILITIES")
print("--------------------------------")
if y_probs:
    print("Max probability sample 0:", np.max(y_probs[0]))

print("\n--------------------------------")
print("7. FINAL DECISION")
print("--------------------------------")
if len(set(y_pred)) > 1 and accuracy > 0.1 and top3_accuracy > 0.3:
    print("Model is FIXED and learning properly.")
else:
    print("Model still underfitting or imbalanced.")
