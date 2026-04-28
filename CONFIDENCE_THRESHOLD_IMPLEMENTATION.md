# Intelligent Confidence-Based Decision Flow

## Overview
The chatbot now intelligently stops asking follow-up questions when the prediction confidence is high enough, rather than always asking a fixed number of questions. This improves UX by showing results early when the diagnosis is clear.

## Key Changes

### Backend (`backend/api/server.py`)

#### 1. New Constants
```python
CONFIDENCE_THRESHOLD = 0.45  # 45% confidence threshold
MAX_FOLLOWUP_QUESTIONS = 3   # Safety limit (fallback)
```

#### 2. New Helper Function: `should_stop_asking()`
```python
def should_stop_asking(top_confidence: float, num_asked: int) -> bool:
    """
    Stops asking if:
    1. Top prediction confidence >= CONFIDENCE_THRESHOLD, OR
    2. Already asked MAX_FOLLOWUP_QUESTIONS
    """
```

#### 3. Updated Response Model
```python
class PredictResponse(BaseModel):
    detected_symptoms: list[str]
    top_predictions: list[dict]
    next_question: str | None
    is_final: bool = False  # NEW: signals prediction is final
    session_id: Optional[str] = None
```

#### 4. Updated `/predict` Endpoint
- Checks confidence of top prediction
- Sets `is_final=True` if confidence >= threshold
- Only asks follow-up questions if `is_final=False`
- Logs decision at every step

#### 5. Updated `/followup` Endpoint
- Rechecks confidence after each user answer
- Stops asking if confidence becomes high enough
- Respects both confidence threshold AND max question limit

### Frontend (`frontend/src/components/ChatInterface.jsx`)

#### 1. New State Variable
```javascript
const [isFinal, setIsFinal] = useState(false);
```

#### 2. Updated `handleResponse()` Function
- Reads `is_final` flag from API response
- Shows different final message based on why it stopped:
  - **High confidence**: "Based on your symptoms, this is the most likely condition. You can start a new check or refine your symptoms."
  - **Max questions reached**: "That's all I need. Your results are shown on the right."

#### 3. Updated Input Placeholder
```javascript
const placeholder = isDone
  ? 'Assessment complete'
  : isFinal
  ? 'Prediction is final'
  : sessionId === null
  ? "Describe your symptoms (e.g. 'fever, cough, headache')..."
  : 'Reply yes / no, or describe how you feel...';
```

#### 4. Updated Input Disabled State
```javascript
disabled={isLoading || isDone || isFinal}
```

#### 5. Updated Reset Handler
- Resets `isFinal` state when starting new assessment

## Decision Flow

### Scenario 1: High Confidence (Early Stop)
```
User: "fever, cough"
↓
Backend predicts: Pneumonia (52% confidence)
↓
52% >= 45% threshold → is_final = true
↓
Frontend: Shows results, disables input
Message: "Based on your symptoms, this is the most likely condition..."
```

### Scenario 2: Low Confidence (Ask Questions)
```
User: "mild headache"
↓
Backend predicts: Migraine (35% confidence)
↓
35% < 45% threshold → is_final = false
↓
Frontend: Asks follow-up question
Message: "Do you have a fever?"
```

### Scenario 3: Confidence Increases After Follow-up
```
User: "mild headache"
↓
Prediction: Migraine (35%) → Ask question
↓
User: "yes, I have a fever"
↓
Prediction: Influenza (48%) → is_final = true
↓
Frontend: Shows results, stops asking
```

### Scenario 4: Max Questions Reached
```
User: "mild symptoms"
↓
Question 1 → Confidence still low
Question 2 → Confidence still low
Question 3 → Confidence still low
↓
len(asked_questions) >= 3 → is_final = true
↓
Frontend: Shows results, stops asking
```

## Configuration

### Tuning Confidence Threshold
Edit `backend/api/server.py`:
```python
CONFIDENCE_THRESHOLD = 0.45  # Adjust between 0.3 and 0.6
```

- **Lower (0.3)**: More aggressive early stopping, fewer questions
- **Higher (0.6)**: More conservative, asks more questions

### Tuning Max Questions
```python
MAX_FOLLOWUP_QUESTIONS = 3  # Adjust as needed
```

## Debug Logging

The backend logs decision points:
```
[should_stop_asking] Confidence 52.00% >= threshold 45.00% → STOP
[should_stop_asking] Confidence 35.00% < threshold, asked 0/3 → CONTINUE
[/predict] Prediction is final, not asking more questions
[/followup] Prediction is final, not asking more questions
```

## Benefits

1. **Better UX**: Results shown immediately when diagnosis is clear
2. **Flexible**: Adapts to confidence level, not fixed question count
3. **Safe**: Falls back to max question limit as safety net
4. **Transparent**: Clear messaging about why assessment ended
5. **Debuggable**: Comprehensive logging for troubleshooting

## Testing Checklist

- [ ] High confidence prediction stops early
- [ ] Low confidence prediction asks questions
- [ ] Confidence increases after follow-up → stops
- [ ] Max questions limit enforced
- [ ] `is_final` flag correctly set in responses
- [ ] Frontend disables input when `is_final=true`
- [ ] Final messages display correctly
- [ ] Reset button works after final prediction
- [ ] Debug logs show decision points
