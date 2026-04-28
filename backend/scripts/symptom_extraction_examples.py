"""
Example usage of the SymptomExtractor module.

This script demonstrates various ways to use the symptom extraction functionality
in the FairMed AI system.
"""

from symptom_extractor import (
    SymptomExtractor, 
    extract_symptoms, 
    extract_symptoms_with_scores
)
import json


def main():
    print("=" * 70)
    print("FAIRMED AI - SYMPTOM EXTRACTION EXAMPLES")
    print("=" * 70)
    
    # Example 1: Basic usage with convenience function
    print("\n[Example 1] Basic symptom extraction")
    print("-" * 70)
    user_input = "I have fever, headache and feeling tired"
    print(f"Input: \"{user_input}\"")
    
    symptoms = extract_symptoms(user_input)
    print(f"Extracted: {symptoms}")
    
    # Example 2: With confidence scores
    print("\n[Example 2] Extraction with confidence scores")
    print("-" * 70)
    user_input = "I'm experiencing chest pain and difficulty breathing"
    print(f"Input: \"{user_input}\"")
    
    results = extract_symptoms_with_scores(user_input)
    for result in results:
        print(f"  - {result['symptom']}: {result['confidence']:.2f} ({result['method']})")
    
    # Example 3: Using the SymptomExtractor class directly
    print("\n[Example 3] Direct class usage with different methods")
    print("-" * 70)
    
    extractor = SymptomExtractor()
    user_input = "My head really hurts and I feel feverish with chills"
    print(f"Input: \"{user_input}\"")
    
    print("\nMethod 1: Exact matching (only direct matches)")
    exact = extractor.extract(user_input, method="exact")
    print(f"  Results: {exact}")
    
    print("\nMethod 2: Fuzzy matching (with variations)")
    fuzzy = extractor.extract(user_input, method="fuzzy")
    print(f"  Results: {fuzzy}")
    
    print("\nMethod 3: Combined (exact first, then fuzzy)")
    combined = extractor.extract(user_input, method="combined")
    print(f"  Results: {combined}")
    
    # Example 4: Detailed extraction with scores
    print("\n[Example 4] Detailed extraction results")
    print("-" * 70)
    user_input = "I have a cough, sore throat, and I feel very tired"
    print(f"Input: \"{user_input}\"")
    
    detailed = extractor.extract_and_score(user_input)
    print("\nDetailed results:")
    for idx, item in enumerate(detailed, 1):
        print(f"  {idx}. {item['symptom']}")
        print(f"     Confidence: {item['confidence']:.2f}")
        print(f"     Method: {item['method']}")
    
    # Example 5: Real-world medical scenarios
    print("\n[Example 5] Real-world medical scenarios")
    print("-" * 70)
    
    scenarios = [
        "I have been having constant headaches for the past 3 days with some dizziness",
        "I'm feeling nauseous, vomiting, and have severe abdominal pain",
        "My chest hurts when I breathe and I feel short of breath",
        "I have a persistent cough, runny nose, and my throat is very sore",
        "I've been experiencing joint pain, especially in my knees and back",
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\nScenario {i}:")
        print(f"  Patient says: \"{scenario}\"")
        
        symptoms = extractor.extract(scenario, method="combined")
        print(f"  Extracted symptoms: {symptoms}")
    
    # Example 6: Integration example for API
    print("\n[Example 6] Integration example for API response")
    print("-" * 70)
    
    user_input = "I have fever and trouble breathing"
    detailed = extractor.extract_and_score(user_input)
    
    # Format as would appear in API response
    api_response = {
        "input_text": user_input,
        "extracted_symptoms": [
            {
                "symptom": item["symptom"],
                "confidence": item["confidence"],
                "method": item["method"]
            }
            for item in detailed
        ],
        "total_found": len(detailed)
    }
    
    print(f"API Response:")
    print(json.dumps(api_response, indent=2))
    
    # Example 7: Available symptoms
    print("\n[Example 7] Sample of available symptoms")
    print("-" * 70)
    
    all_symptoms = extractor.get_symptom_list()
    print(f"Total symptoms in database: {len(all_symptoms)}")
    print(f"\nFirst 20 symptoms:")
    for symptom in all_symptoms[:20]:
        print(f"  - {symptom}")
    
    print(f"\n... and {len(all_symptoms) - 20} more")
    
    print("\n" + "=" * 70)
    print("END OF EXAMPLES")
    print("=" * 70)


if __name__ == "__main__":
    main()
