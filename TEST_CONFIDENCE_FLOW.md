# Testing Confidence-Based Decision Flow

## Quick Start
- **Frontend**: http://localhost:5174
- **Backend**: http://localhost:8000
- Both servers are running and auto-reload on changes

## Test Scenarios

### Test 1: High Confidence (Early Stop)
**Goal**: Verify chatbot stops asking when confidence is high

1. Open http://localhost:5174
2. Enter age and gender
3. Type: `"fever and cough"`
4. Expected:
   - ✅ Predictions show (likely Pneumonia, Influenza, etc.)
   - ✅ Input placeholder changes to "Prediction is final"
   - ✅ Input field is disabled
   - ✅ Message: "Based on your symptoms, this is the most likely condition..."
   - ✅ "New" button appears instead of "Send"
5. Check backend logs:
   - Look for: `[should_stop_asking] Confidence X% >= threshold 45% → STOP`

### Test 2: Low Confidence (Ask Questions)
**Goal**: Verify chatbot asks questions when confidence is low

1. Type: `"mild headache"`
2. Expected:
   - ✅ Predictions show
   - ✅ Input placeholder: "Reply yes / no, or describe how you feel..."
   - ✅ Input field is enabled
   - ✅ Bot asks a follow-up question (e.g., "Do you have a fever?")
3. Check backend logs:
   - Look for: `[should_stop_asking] Confidence X% < threshold, asked 0/3 → CONTINUE`

### Test 3: Confidence Increases After Follow-up
**Goal**: Verify chatbot stops when confidence becomes high

1. Type: `"mild headache"`
2. Bot asks: "Do you have a fever?"
3. Type: `"yes"`
4. Expected:
   - ✅ Predictions update
   - ✅ If confidence now >= 45%, input disables and shows final message
   - ✅ If confidence still < 45%, bot asks another question
5. Check backend logs:
   - Look for confidence values increasing

### Test 4: Max Questions Limit
**Goal**: Verify chatbot stops after 3 questions even if confidence is low

1. Type: `"very mild symptoms"`
2. Answer 3 follow-up questions
3. Expected:
   - ✅ After 3rd question, input disables
   - ✅ Message: "That's all I need. Your results are shown on the right."
   - ✅ "New" button appears
4. Check backend logs:
   - Look for: `[should_stop_asking] Asked 3 questions >= max 3 → STOP`

### Test 5: Reset and New Assessment
**Goal**: Verify reset functionality

1. After any assessment, click "New" button
2. Expected:
   - ✅ Setup screen appears again
   - ✅ Chat clears
   - ✅ Can enter new age/gender
   - ✅ Can start new assessment

## Backend Debug Logging

Watch the backend terminal for these log patterns:

```
[/predict] Symptoms: ['fever', 'cough']
[/predict] Predictions: [('Pneumonia', 52.3), ...]
[should_stop_asking] Confidence 52.30% >= threshold 45.00% → STOP
[/predict] Prediction is final, not asking more questions
```

Or for low confidence:

```
[/predict] Symptoms: ['headache']
[/predict] Predictions: [('Migraine', 35.1), ...]
[should_stop_asking] Confidence 35.10% < threshold, asked 0/3 → CONTINUE
[select_next_question] Selected: 'Do you have a fever?' (symptom: fever)
```

## Adjusting Threshold

To make the chatbot more/less aggressive:

1. Edit `backend/api/server.py`
2. Find: `CONFIDENCE_THRESHOLD = 0.45`
3. Change to:
   - `0.35` for more aggressive early stopping
   - `0.55` for more conservative (asks more questions)
4. Backend auto-reloads
5. Test again

## Common Issues

### Issue: Chatbot always asks 3 questions
- **Cause**: Confidence never reaches threshold
- **Fix**: Lower `CONFIDENCE_THRESHOLD` value

### Issue: Chatbot stops too early
- **Cause**: Confidence threshold too low
- **Fix**: Raise `CONFIDENCE_THRESHOLD` value

### Issue: `is_final` not in response
- **Cause**: Backend didn't reload
- **Fix**: Check backend logs, manually restart if needed

### Issue: Input still enabled after final prediction
- **Cause**: Frontend didn't receive `is_final=true`
- **Fix**: Check browser console for API errors

## Success Criteria

✅ All 5 test scenarios pass
✅ Backend logs show correct decision points
✅ Frontend UI responds correctly to `is_final` flag
✅ Reset button works
✅ No console errors
