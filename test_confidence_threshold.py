"""
Test verification for confidence threshold and question stopping logic.

This script verifies:
1. Confidence threshold at 0.35 stops asking when confident
2. Max 2 follow-up questions hard limit
3. No duplicate questions are asked
4. is_final flag is set correctly
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_high_confidence_stops_early():
    """Test that high confidence stops asking questions immediately."""
    print("\n" + "="*70)
    print("TEST 1: High Confidence Should Stop Asking")
    print("="*70)
    
    # Symptoms that should give high confidence
    response = requests.post(f"{API_URL}/predict", json={
        "message": "fever and cough",
        "age": 30,
        "gender": "male"
    })
    
    data = response.json()
    print(f"\n✓ Initial prediction:")
    print(f"  Symptoms detected: {data['detected_symptoms']}")
    print(f"  Top disease: {data['top_predictions'][0]['disease']}")
    print(f"  Confidence: {data['top_predictions'][0]['confidence']:.1%}")
    print(f"  Next question: {data.get('next_question')}")
    print(f"  Is final: {data['is_final']}")
    
    if data['is_final']:
        print("\n✓ SUCCESS: is_final=True, no more questions asked")
        return True
    elif data['top_predictions'][0]['confidence'] >= 0.35:
        print(f"\n✗ FAIL: Confidence {data['top_predictions'][0]['confidence']:.1%} >= 0.35 but is_final=False")
        return False
    
    return True


def test_low_confidence_asks_followup():
    """Test that low confidence asks follow-up questions but not more than 2."""
    print("\n" + "="*70)
    print("TEST 2: Low Confidence Should Ask 1-2 Follow-ups (Not More)")
    print("="*70)
    
    # Symptoms that might give lower confidence
    response = requests.post(f"{API_URL}/predict", json={
        "message": "headache",
        "age": 30,
        "gender": "male"
    })
    
    data = response.json()
    session_id = data.get('session_id')
    print(f"\n✓ Initial prediction (Session: {session_id[:8]}...):")
    print(f"  Symptoms: {data['detected_symptoms']}")
    print(f"  Confidence: {data['top_predictions'][0]['confidence']:.1%}")
    print(f"  Next question: {data.get('next_question')}")
    print(f"  Question count so far: 0")
    
    questions_asked = 0
    next_question = data.get('next_question')
    next_symptom = data.get('next_symptom_key')
    
    if next_question:
        questions_asked += 1
        print(f"\n✓ Follow-up 1: {next_question}")
        print(f"  Symptom key: {next_symptom}")
        
        # Simulate user answering "no"
        response = requests.post(f"{API_URL}/followup", json={
            "session_id": session_id,
            "new_answer": {next_symptom: 0},
            "age": 30,
            "gender": "male"
        })
        
        data = response.json()
        print(f"  → Confidence after answer: {data['top_predictions'][0]['confidence']:.1%}")
        print(f"  → Is final: {data['is_final']}")
        
        next_question = data.get('next_question')
        next_symptom = data.get('next_symptom_key')
        
        if next_question and not data['is_final']:
            questions_asked += 1
            print(f"\n✓ Follow-up 2: {next_question}")
            print(f"  Symptom key: {next_symptom}")
            
            # Simulate user answering "no" again
            response = requests.post(f"{API_URL}/followup", json={
                "session_id": session_id,
                "new_answer": {next_symptom: 0},
                "age": 30,
                "gender": "male"
            })
            
            data = response.json()
            print(f"  → Confidence after answer: {data['top_predictions'][0]['confidence']:.1%}")
            print(f"  → Is final: {data['is_final']}")
            print(f"  → Next question: {data.get('next_question')}")
            
            if data.get('next_question'):
                questions_asked += 1
                print(f"\n✗ FAIL: Asked {questions_asked} questions, max should be 2")
                return False
    
    print(f"\n✓ SUCCESS: Asked {questions_asked} questions (max 2), is_final={data['is_final']}")
    return True


def test_no_duplicate_questions():
    """Test that the same question is never asked twice."""
    print("\n" + "="*70)
    print("TEST 3: No Duplicate Questions")
    print("="*70)
    
    response = requests.post(f"{API_URL}/predict", json={
        "message": "feeling unwell",
        "age": 30,
        "gender": "female"
    })
    
    data = response.json()
    session_id = data.get('session_id')
    asked_symptoms = set()
    
    print(f"\n✓ Initial prediction (Session: {session_id[:8]}...):")
    print(f"  Symptoms: {data['detected_symptoms']}")
    
    next_question = data.get('next_question')
    next_symptom = data.get('next_symptom_key')
    question_num = 0
    
    while next_question and question_num < 3:  # Allow up to 3 iterations for safety
        question_num += 1
        asked_symptoms.add(next_symptom)
        print(f"\n✓ Question {question_num}: {next_question}")
        print(f"  Symptom key: {next_symptom}")
        
        # Simulate user answering
        response = requests.post(f"{API_URL}/followup", json={
            "session_id": session_id,
            "new_answer": {next_symptom: 1},  # Say yes
            "age": 30,
            "gender": "female"
        })
        
        data = response.json()
        next_question = data.get('next_question')
        next_symptom = data.get('next_symptom_key')
        
        if next_symptom in asked_symptoms:
            print(f"\n✗ FAIL: Duplicate question detected! Already asked about {next_symptom}")
            return False
        
        if not next_question or data['is_final']:
            break
    
    print(f"\n✓ SUCCESS: Asked {question_num} questions, no duplicates")
    return True


if __name__ == "__main__":
    print("CONFIDENCE THRESHOLD VERIFICATION TESTS")
    print("=" * 70)
    print(f"Testing API at {API_URL}")
    print(f"Confidence Threshold: 0.35 (35%)")
    print(f"Max Follow-up Questions: 2")
    
    results = []
    
    try:
        results.append(("High Confidence", test_high_confidence_stops_early()))
    except Exception as e:
        print(f"\n✗ ERROR in test 1: {e}")
        results.append(("High Confidence", False))
    
    try:
        results.append(("Low Confidence", test_low_confidence_asks_followup()))
    except Exception as e:
        print(f"\n✗ ERROR in test 2: {e}")
        results.append(("Low Confidence", False))
    
    try:
        results.append(("No Duplicates", test_no_duplicate_questions()))
    except Exception as e:
        print(f"\n✗ ERROR in test 3: {e}")
        results.append(("No Duplicates", False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n✓ All tests PASSED!")
    else:
        print("\n✗ Some tests FAILED")
    
    print("="*70)
