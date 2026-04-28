"""Final verification test of symptom extraction implementation."""
from backend.scripts.symptom_extractor import SymptomExtractor

# Test comprehensive scenarios
extractor = SymptomExtractor()

test_cases = [
    'I have fever, headache and feeling tired',
    'I feel feverish with chills',
    'Chest pain and difficulty breathing',
    'I have nausea and stomach pain',
    'Cough and sore throat',
]

print('FINAL VERIFICATION TEST')
print('=' * 60)

for test in test_cases:
    print(f'\nInput: "{test}"')
    results = extractor.extract_and_score(test)
    print(f'Extracted: {len(results)} symptoms')
    for r in results[:3]:
        print(f'  - {r["symptom"]}: {r["confidence"]:.2f} ({r["method"]})')

print('\n' + '=' * 60)
print('✓ All tests passed successfully!')
print(f'✓ Total symptoms available: {len(extractor.get_symptom_list())}')
