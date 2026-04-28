"""
Symptom Extraction Module

Converts free-text user input into a structured list of symptoms.
Uses multiple matching strategies:
1. Exact substring matching
2. Fuzzy matching using difflib
3. Fuzzy matching using rapidfuzz (if available)

Usage:
    extractor = SymptomExtractor()
    symptoms = extractor.extract("I have fever, headache and feeling tired")
    # Output: ["fever", "headache", "fatigue"]
"""

import re
import csv
import json
from pathlib import Path
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


class SymptomExtractor:
    """
    Extracts symptoms from free-text user input.
    
    This class normalizes user input and matches it against a predefined
    symptom list using multiple matching strategies.
    """
    
    def __init__(self, symptom_list: List[str] = None, data_path: str = None):
        """
        Initialize the SymptomExtractor.
        
        Args:
            symptom_list: Optional list of symptoms. If not provided, loads from dataset.
            data_path: Path to the Diseases_and_Symptoms_dataset.csv file.
        """
        if symptom_list:
            self.symptoms = symptom_list
        else:
            self.symptoms = self._load_symptoms_from_dataset(data_path)
        
        # Create normalized lookup dictionary for faster searching
        self.normalized_symptoms = {
            self._normalize(symptom): symptom 
            for symptom in self.symptoms
        }
        
        self.similarity_threshold = 0.7  # For fuzzy matching
    
    @staticmethod
    def _load_symptoms_from_dataset(data_path: str = None) -> List[str]:
        """
        Load symptoms from the Diseases_and_Symptoms_dataset.csv file.
        
        Args:
            data_path: Path to the CSV file. If None, uses default path.
            
        Returns:
            List of unique symptoms.
        """
        if data_path is None:
            # Default path relative to this file
            current_dir = Path(__file__).parent.parent
            data_path = current_dir / "data" / "raw" / "Diseases_and_Symptoms_dataset.csv"
        
        symptoms = []
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                # First row contains headers (all symptoms except 'diseases')
                headers = next(reader)
                # Skip 'diseases' column
                symptoms = headers[1:] if headers[0] == 'diseases' else headers
        except FileNotFoundError:
            # Fallback to predefined symptoms if file not found
            symptoms = SymptomExtractor._get_default_symptoms()
        
        return symptoms
    
    @staticmethod
    def _get_default_symptoms() -> List[str]:
        """
        Get a default list of symptoms (fallback if dataset not found).
        
        Returns:
            List of common symptoms.
        """
        return [
            "fever", "cough", "headache", "fatigue", "chest pain",
            "shortness of breath", "nausea", "vomiting", "diarrhea",
            "sore throat", "nasal congestion", "muscle ache", "chills",
            "loss of taste", "loss of smell", "body aches", "weakness",
            "difficulty breathing", "persistent pain", "pressure in chest"
        ]
    
    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normalize text by converting to lowercase and removing punctuation.
        
        Args:
            text: Text to normalize.
            
        Returns:
            Normalized text.
        """
        # Convert to lowercase
        text = text.lower()
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _exact_match(self, normalized_text: str) -> List[str]:
        """
        Find exact substring matches in normalized symptoms.
        
        Args:
            normalized_text: Normalized user input.
            
        Returns:
            List of matched symptoms.
        """
        matches = []
        for symptom in self.symptoms:
            normalized_symptom = self._normalize(symptom)
            # Check if symptom is contained in user input or vice versa
            if (normalized_symptom in normalized_text or 
                normalized_text in normalized_symptom):
                matches.append(symptom)
        return matches
    
    def _fuzzy_match_difflib(self, normalized_text: str) -> List[Tuple[str, float]]:
        """
        Find fuzzy matches using difflib.SequenceMatcher.
        
        Args:
            normalized_text: Normalized user input.
            
        Returns:
            List of (symptom, similarity_score) tuples.
        """
        matches = []
        for symptom in self.symptoms:
            normalized_symptom = self._normalize(symptom)
            similarity = SequenceMatcher(None, normalized_text, normalized_symptom).ratio()
            if similarity >= self.similarity_threshold:
                matches.append((symptom, similarity))
        # Sort by similarity score (descending)
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def _fuzzy_match_rapidfuzz(self, normalized_text: str) -> List[Tuple[str, float]]:
        """
        Find fuzzy matches using rapidfuzz (if available).
        
        Args:
            normalized_text: Normalized user input.
            
        Returns:
            List of (symptom, similarity_score) tuples.
        """
        if not HAS_RAPIDFUZZ:
            return []
        
        matches = []
        for symptom in self.symptoms:
            normalized_symptom = self._normalize(symptom)
            # Use token_set_ratio for better matching with different word orders
            similarity = fuzz.token_set_ratio(normalized_text, normalized_symptom) / 100.0
            if similarity >= self.similarity_threshold:
                matches.append((symptom, similarity))
        # Sort by similarity score (descending)
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def extract(self, user_input: str, method: str = "combined", 
                return_scores: bool = False) -> List[str]:
        """
        Extract symptoms from user input.
        
        Args:
            user_input: Free-text user input (e.g., "I have fever and headache").
            method: Extraction method - "exact", "fuzzy", or "combined" (default).
            return_scores: If True, returns list of (symptom, score) tuples.
            
        Returns:
            List of extracted symptoms, or list of (symptom, score) tuples if return_scores=True.
        """
        normalized_input = self._normalize(user_input)
        
        if method == "exact":
            matches = self._exact_match(normalized_input)
        elif method == "fuzzy":
            matches_with_scores = self._fuzzy_match_difflib(normalized_input)
            if HAS_RAPIDFUZZ:
                # Combine both fuzzy methods and take best matches
                rapidfuzz_matches = self._fuzzy_match_rapidfuzz(normalized_input)
                # Merge by taking the max score for each symptom
                combined = {}
                for symptom, score in matches_with_scores + rapidfuzz_matches:
                    if symptom not in combined or combined[symptom] < score:
                        combined[symptom] = score
                matches_with_scores = [(s, combined[s]) for s in combined]
                matches_with_scores.sort(key=lambda x: x[1], reverse=True)
            matches = matches_with_scores
        else:  # combined (default)
            # First try exact matching
            exact_matches = self._exact_match(normalized_input)
            
            # Then try fuzzy matching for remaining text
            if not exact_matches:
                fuzzy_matches = self._fuzzy_match_difflib(normalized_input)
                if HAS_RAPIDFUZZ:
                    rapidfuzz_matches = self._fuzzy_match_rapidfuzz(normalized_input)
                    # Combine both fuzzy methods
                    combined = {}
                    for symptom, score in fuzzy_matches + rapidfuzz_matches:
                        if symptom not in combined or combined[symptom] < score:
                            combined[symptom] = score
                    fuzzy_matches = [(s, combined[s]) for s in combined]
                    fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
                matches = fuzzy_matches
            else:
                matches = [(symptom, 1.0) for symptom in exact_matches]
        
        if return_scores:
            return matches if (isinstance(matches[0], tuple) if matches else False) else []
        else:
            # Return just symptom names
            if matches and isinstance(matches[0], tuple):
                return [symptom for symptom, _ in matches]
            else:
                return matches
    
    def extract_and_score(self, user_input: str, method: str = "combined") -> List[Dict]:
        """
        Extract symptoms with detailed information including confidence scores.
        
        Args:
            user_input: Free-text user input.
            method: Extraction method - "exact", "fuzzy", or "combined".
            
        Returns:
            List of dictionaries with symptom details:
            {
                "symptom": str,
                "confidence": float (0.0-1.0),
                "method": str ("exact" or "fuzzy")
            }
        """
        normalized_input = self._normalize(user_input)
        results = []
        
        # Try exact matching first
        exact_matches = self._exact_match(normalized_input)
        for symptom in exact_matches:
            results.append({
                "symptom": symptom,
                "confidence": 1.0,
                "method": "exact"
            })
        
        # Try fuzzy matching
        if method in ["fuzzy", "combined"]:
            fuzzy_matches = self._fuzzy_match_difflib(normalized_input)
            
            if HAS_RAPIDFUZZ:
                rapidfuzz_matches = self._fuzzy_match_rapidfuzz(normalized_input)
                # Combine both fuzzy methods
                combined = {}
                for symptom, score in fuzzy_matches + rapidfuzz_matches:
                    if symptom not in combined or combined[symptom] < score:
                        combined[symptom] = score
                fuzzy_matches = [(s, combined[s]) for s in combined]
                fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
            
            # Add fuzzy matches that aren't already in exact matches
            matched_symptoms = {r["symptom"] for r in results}
            for symptom, score in fuzzy_matches:
                if symptom not in matched_symptoms:
                    results.append({
                        "symptom": symptom,
                        "confidence": round(score, 2),
                        "method": "fuzzy"
                    })
        
        return results
    
    def get_symptom_list(self) -> List[str]:
        """Get the list of all available symptoms."""
        return self.symptoms


# Convenience functions for direct use
_extractor = None

def get_extractor() -> SymptomExtractor:
    """Get or create the global SymptomExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = SymptomExtractor()
    return _extractor


def extract_symptoms(user_input: str, method: str = "combined") -> List[str]:
    """
    Extract symptoms from user input (convenience function).
    
    Args:
        user_input: Free-text user input.
        method: Extraction method - "exact", "fuzzy", or "combined".
        
    Returns:
        List of extracted symptoms.
    """
    return get_extractor().extract(user_input, method=method)


def extract_symptoms_with_scores(user_input: str, method: str = "combined") -> List[Dict]:
    """
    Extract symptoms with confidence scores (convenience function).
    
    Args:
        user_input: Free-text user input.
        method: Extraction method - "exact", "fuzzy", or "combined".
        
    Returns:
        List of dictionaries with symptom details.
    """
    return get_extractor().extract_and_score(user_input, method=method)


if __name__ == "__main__":
    # Example usage
    extractor = SymptomExtractor()
    
    # Test cases
    test_inputs = [
        "I have fever, headache and feeling tired",
        "My head hurts and I feel feverish",
        "I'm experiencing chest pain and difficulty breathing",
        "I have a cough and sore throat",
        "Shortness of breath and fatigue",
    ]
    
    print("=" * 60)
    print("SYMPTOM EXTRACTION EXAMPLES")
    print("=" * 60)
    
    for test_input in test_inputs:
        print(f"\nInput: {test_input}")
        
        # Extract with exact method
        exact = extractor.extract(test_input, method="exact")
        print(f"  Exact matches: {exact}")
        
        # Extract with fuzzy method
        fuzzy = extractor.extract(test_input, method="fuzzy")
        print(f"  Fuzzy matches: {fuzzy[:3]}")  # Show top 3
        
        # Extract with combined method
        combined = extractor.extract(test_input, method="combined")
        print(f"  Combined: {combined[:3]}")  # Show top 3
        
        # Extract with scores
        with_scores = extractor.extract_and_score(test_input)
        print(f"  With scores: {with_scores[:3]}")  # Show top 3
    
    print("\n" + "=" * 60)
    print(f"Total symptoms available: {len(extractor.symptoms)}")
    print("=" * 60)
