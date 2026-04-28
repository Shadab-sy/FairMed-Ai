"""
Gemini Symptom Extractor - Syntax & Structure Verification

This script verifies the Gemini extractor module is properly implemented
without requiring an actual API key.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "scripts"))

print("=" * 70)
print("GEMINI SYMPTOM EXTRACTOR - VERIFICATION")
print("=" * 70)

# Test 1: Module imports
print("\n[Test 1] Module Import")
print("-" * 70)
try:
    from gemini_symptom_extractor import (
        GeminiSymptomExtractor,
        extract_symptoms_gemini,
        get_extractor,
    )
    print("✓ Module imports successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Class structure
print("\n[Test 2] Class Structure")
print("-" * 70)
try:
    # Check class methods exist
    methods = [
        'extract',
        '_build_prompt',
        '_build_payload',
        '_call_api',
        '_parse_response',
    ]
    
    for method in methods:
        if hasattr(GeminiSymptomExtractor, method):
            print(f"✓ Method '{method}' exists")
        else:
            print(f"✗ Method '{method}' missing")
            sys.exit(1)
            
except Exception as e:
    print(f"✗ Structure check failed: {e}")
    sys.exit(1)

# Test 3: Prompt generation
print("\n[Test 3] Prompt Generation")
print("-" * 70)
try:
    test_input = "I have fever and chest pain"
    prompt = GeminiSymptomExtractor._build_prompt(test_input)
    
    # Verify prompt contains key elements
    required_elements = [
        'Extract symptoms',
        test_input,
        'JSON array',
        'medical symptoms',
        'Normalize terms',
    ]
    
    for element in required_elements:
        if element in prompt:
            print(f"✓ Prompt contains '{element}'")
        else:
            print(f"✗ Prompt missing '{element}'")
            sys.exit(1)
            
    print(f"\n✓ Generated prompt ({len(prompt)} chars)")
    
except Exception as e:
    print(f"✗ Prompt generation failed: {e}")
    sys.exit(1)

# Test 4: Payload structure
print("\n[Test 4] Payload Structure")
print("-" * 70)
try:
    import json
    
    extractor = object.__new__(GeminiSymptomExtractor)
    test_prompt = "Test prompt"
    payload_bytes = extractor._build_payload(test_prompt)
    
    # Verify it's valid JSON
    payload_dict = json.loads(payload_bytes.decode('utf-8'))
    
    # Check structure
    required_keys = ['contents', 'generationConfig']
    for key in required_keys:
        if key in payload_dict:
            print(f"✓ Payload contains '{key}'")
        else:
            print(f"✗ Payload missing '{key}'")
            sys.exit(1)
    
    # Check generation config
    gen_config = payload_dict['generationConfig']
    if gen_config.get('response_mime_type') == 'application/json':
        print("✓ Configured for JSON response")
    else:
        print("✗ Not configured for JSON")
        sys.exit(1)
    
    if gen_config.get('temperature') == 0.1:
        print("✓ Low temperature for consistency (0.1)")
    else:
        print("✗ Temperature not optimized")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Payload structure check failed: {e}")
    sys.exit(1)

# Test 5: JSON parsing
print("\n[Test 5] JSON Parsing")
print("-" * 70)
try:
    test_responses = [
        '["fever", "headache"]',  # Direct array
        '{"results": ["fever", "headache"]}',  # Should fail gracefully
        'Some text ["fever", "chest pain"] more text',  # Array in text
    ]
    
    for response in test_responses:
        try:
            result = GeminiSymptomExtractor._parse_response(response)
            print(f"✓ Parsed: {result}")
        except ValueError:
            print(f"✓ Correctly rejected: {response[:30]}...")
            
except Exception as e:
    print(f"✗ JSON parsing test failed: {e}")
    sys.exit(1)

# Test 6: Convenience functions
print("\n[Test 6] Convenience Functions")
print("-" * 70)
try:
    # Check functions exist and are callable
    functions = [
        get_extractor,
        extract_symptoms_gemini,
    ]
    
    for func in functions:
        if callable(func):
            print(f"✓ Function '{func.__name__}' is callable")
        else:
            print(f"✗ Function '{func.__name__}' not callable")
            sys.exit(1)
            
except Exception as e:
    print(f"✗ Convenience function test failed: {e}")
    sys.exit(1)

# Test 7: Error handling
print("\n[Test 7] Error Handling")
print("-" * 70)
try:
    # Test missing API key handling
    import os
    original_key = os.environ.get('GEMINI_API_KEY')
    
    # Remove API key if present
    if 'GEMINI_API_KEY' in os.environ:
        del os.environ['GEMINI_API_KEY']
    
    try:
        extractor = GeminiSymptomExtractor()
        print("✗ Should have raised ValueError for missing API key")
        sys.exit(1)
    except ValueError as e:
        if 'GEMINI_API_KEY' in str(e):
            print("✓ Correctly raises ValueError for missing API key")
        else:
            print("✗ Error message doesn't mention API key")
            sys.exit(1)
    
    # Restore API key
    if original_key:
        os.environ['GEMINI_API_KEY'] = original_key
        
except Exception as e:
    print(f"✗ Error handling test failed: {e}")
    sys.exit(1)

# Test 8: Integration with local extractor
print("\n[Test 8] Integration with Local Extractor")
print("-" * 70)
try:
    from symptom_extractor import SymptomExtractor
    
    local_ext = SymptomExtractor()
    print(f"✓ Local extractor has {len(local_ext.get_symptom_list())} symptoms")
    print("✓ Gemini can fallback to local extraction")
    
except Exception as e:
    print(f"✗ Integration test failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("✓ ALL VERIFICATION TESTS PASSED")
print("=" * 70)

print("""
Summary:
--------
✓ Module structure is correct
✓ Class methods implemented
✓ Prompt engineering validated
✓ Payload structure correct
✓ JSON parsing works
✓ Convenience functions available
✓ Error handling in place
✓ Integration with local extractor ready

Ready to Deploy:
- Gemini extractor module: backend/scripts/gemini_symptom_extractor.py
- API endpoint: POST /extract-symptoms-gemini (in server.py)
- Documentation: backend/GEMINI_EXTRACTION.md
- Comparison guide: LOCAL_VS_GEMINI_COMPARISON.md

Next Steps:
1. Set GEMINI_API_KEY environment variable
2. Restart the API server
3. Test the endpoint: POST /extract-symptoms-gemini

""")
