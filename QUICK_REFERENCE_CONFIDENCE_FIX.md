# Quick Reference: Confidence Threshold Fix

## What Changed

```
CONFIDENCE_THRESHOLD: 0.45 → 0.35 (35% confidence = sufficient)
MAX_FOLLOWUP_QUESTIONS: 3 → 2 (hard limit on follow-ups)
```

## 3 Key Fixes

### Fix 1: Lower Threshold
Bot now stops asking when confidence ≥ 35%, not 45%
- More responsive recommendations
- Fewer unnecessary follow-up questions

### Fix 2: Limit Questions
Hard limit: never ask more than 2 follow-up questions
- Prevents infinite loops
- Faster user experience

### Fix 3: Backend Provides Symptom Key
Response includes `next_symptom_key` field
- Frontend no longer needs to extract symptom from question text
- Eliminates extraction failures ("lost your appetite" ≠ "loss of appetite")

## Before vs After

### Before (Problem)
```
User: "fever cold"
↓
Bot: Confidence 40%, but 40% < 45% threshold
↓
Bot: "Have you lost your appetite?"
↓
User: "Yes"
↓
Bot: "Have you lost your appetite?" ← REPEAT (extraction failed)
↓
Infinite loop / repeated questions
```

### After (Fixed)
```
User: "fever cold"
↓
Bot: Confidence 42%, 42% >= 35% threshold
↓
is_final = true
↓
Bot: "Based on your symptoms, this is the most likely condition."
↓
Input disabled, conversation ends ✓
```

## How to Verify It Works

**Test 1: Fast Path** (High Confidence)
```
Input: "fever cold"
Expected: Immediate result, no follow-up questions
Check: is_final = true in response
```

**Test 2: Follow-ups** (Low Confidence)
```
Input: "mild discomfort"
Expected: Up to 2 follow-up questions max, then stop
Check: Asked >2 = FAIL
```

**Test 3: No Repeats** (Question Tracking)
```
Follow multi-question flow
Expected: Each question asked once
Check: Logs for duplicates = FAIL
```

## Key Code Locations

| Component | Location | What to Look For |
|-----------|----------|------------------|
| Threshold Config | server.py L35-40 | `CONFIDENCE_THRESHOLD = 0.35` |
| Stop Logic | server.py L360-389 | `should_stop_asking()` function |
| Response Model | server.py L68-76 | `next_symptom_key` field |
| /predict endpoint | server.py L795-805 | Includes `next_symptom_key` |
| /followup endpoint | server.py L910-920 | Includes `next_symptom_key` |
| Frontend | ChatInterface.jsx L216 | Uses `data.next_symptom_key` |

## Logs to Watch

```
[should_stop_asking] Confidence 42% >= threshold 35% → STOP
[should_stop_asking] Asked 2 questions >= max 2 → STOP
[select_next_question] Already asked: loss_of_appetite
```

If you see duplicate questions, the backend didn't reload. Restart the server.

## Deployment Steps

1. ✅ Backend code updated (done)
2. ✅ Frontend code updated (done)
3. ⏳ Restart backend server
4. ⏳ Hard refresh frontend (Ctrl+F5)
5. ⏳ Test with fresh session (new user)
6. ⏳ Run `python test_confidence_threshold.py`

## Expected Flow Diagram

```
┌─────────────────┐
│ User Input      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ predict()       │
└────────┬────────┘
         │
         ▼
    Is confidence >= 0.35?
    /                      \
  YES                        NO
   │                          │
   ▼                          ▼
is_final=true       Any unanswered questions?
   │                   /            \
   │                 YES             NO
   │                  │              │
   │                  ▼              ▼
   │            Asked < 2?       is_final=true
   │            /        \           │
   │          YES        NO          │
   │           │          │          │
   │           ▼          ▼          ▼
   │        Ask Q1   is_final   Show
   │         │        true      Result
   │         │         │           │
   │         ▼         ▼           ▼
   └─────→ Return response ←──────┘
           (next_question, 
            is_final, 
            next_symptom_key)
```

## Summary
✅ Stops intelligently at 35% confidence
✅ Never asks more than 2 follow-ups  
✅ Provides symptom key to prevent extraction bugs
✅ Tracks all asked questions to prevent repeats
✅ Frontend respects `is_final` flag

Ready to test!
