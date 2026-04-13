# Matching Policy Specification  
## RaceWrangler – OCR → Competitor Association  
## Version: April 2026

This document defines the rules RaceWrangler uses to match OCR‑extracted **car numbers** and **class letters** to a specific competitor entry.  
It ensures deterministic behavior even when OCR output is ambiguous, incomplete, or low‑confidence.

---

# 1. Purpose

The matching policy determines how the system:

- interprets OCR output  
- resolves ambiguity  
- selects the correct competitor  
- triggers human review when needed  
- handles multiple possible matches  
- handles missing or partial class information  
- handles leading‑zero numbers  
- handles multiple class systems (TT + AX)  

This policy prevents Copilot from guessing and ensures consistent behavior across all events.

---

# 2. Inputs to the Matching Process

The matching engine receives:

```
{
  "number_raw": "<string or null>",
  "number_normalized": "<string or null>",   // leading zeros preserved
  "class_raw": "<string or null>",
  "class_normalized": "<string or null>",
  "confidence_number": <0.0–1.0>,
  "confidence_class": <0.0–1.0>
}
```

And the event’s competitor list:

```
[
  {
    "competitor_id": "...",
    "number": "<string>",          // leading zeros preserved
    "class": "<string>",           // normalized class code
    "run_group": "<string>"
  },
  ...
]
```

---

# 3. Confidence Thresholds

These thresholds determine when the system trusts OCR output.

## 3.1 Number Confidence Thresholds
- **High confidence:** ≥ 0.80  
- **Medium confidence:** 0.50–0.79  
- **Low confidence:** < 0.50  

## 3.2 Class Confidence Thresholds
- **High confidence:** ≥ 0.70  
- **Medium confidence:** 0.40–0.69  
- **Low confidence:** < 0.40  

Class letters are harder to read reliably, so thresholds differ.

---

# 4. Matching Rules (Number First)

RaceWrangler always matches **by number first**, then uses class to disambiguate.

## 4.1 Exact Number Match (High Confidence)
If:
- `number_normalized` matches a competitor’s number **exactly**, and  
- `confidence_number ≥ high threshold`

→ **Auto‑match**.

## 4.2 Exact Number Match (Medium Confidence)
If:
- number matches exactly  
- confidence is medium  

→ **Match tentatively**, but flag for Timing Console review.

## 4.3 Exact Number Match (Low Confidence)
If:
- number matches exactly  
- confidence is low  

→ **Do not auto‑match**.  
→ Send to Timing Console for manual confirmation.

## 4.4 Multiple Competitors With Same Number
If multiple competitors share the same number (rare but possible):

Use class to disambiguate:
- If class matches exactly → match  
- If class is missing or low‑confidence → send to Timing Console  
- If class conflicts → send to Timing Console  

---

# 5. Class‑Based Disambiguation

Class is used **only** when number alone is insufficient.

## 5.1 Class Exact Match (High Confidence)
If:
- number matches multiple competitors  
- class matches exactly  
- class confidence ≥ high threshold  

→ **Auto‑select correct competitor**.

## 5.2 Class Exact Match (Medium Confidence)
→ Tentative match, flagged for review.

## 5.3 Class Low Confidence or Missing
→ Do not use class for disambiguation.  
→ Send to Timing Console.

---

# 6. Handling Missing or Unreadable Class

If number matches exactly but class is unreadable:

- Accept the number match  
- Ignore class  
- Flag for Timing Console only if:
  - multiple competitors share the number  
  - class mismatch is suspected  
  - Number Mistake Detection triggers  

---

# 7. Handling Multiple Class Systems (TT + AX)

Some competitors display:
- a permanent **Time Trials** class  
- a temporary **Autocross** class  
- stacked or adjacent class blocks  

OCR may detect both.

## 7.1 Class Selection Priority
1. **Autocross class** (event class list)  
2. **Time Trials class** (ignored unless AX class missing)  
3. **Other markings** (ignored)

## 7.2 If OCR detects multiple class-like strings
- Keep all candidates  
- Attempt to match AX class first  
- If AX class not found, fall back to TT class  
- If still ambiguous → Timing Console review  

---

# 8. Leading Zero Handling

Leading zeros are **meaningful**.

- `"01"` ≠ `"1"`  
- `"007"` ≠ `"7"`  

Matching must be **string‑based**, not integer‑based.

OCR must preserve leading zeros exactly.

---

# 9. Ambiguous OCR Output

If OCR returns multiple candidates (e.g., `"17"` vs `"11"`):

- Prefer the candidate with higher confidence  
- If confidence difference < 0.15 → treat as ambiguous  
- If ambiguous → Timing Console review  

---

# 10. When to Trigger Human Review

Send to Timing Console when:

- number confidence < low threshold  
- class confidence < low threshold AND class needed for disambiguation  
- multiple competitors share the same number  
- OCR returns multiple number candidates  
- OCR returns multiple class candidates  
- class conflicts with competitor record  
- Number Mistake Detection flags a mismatch  
- competitor not found in event list  

---

# 11. Human Correction Workflow

When Timing Staff corrects:
- number  
- class  
- competitor selection  

The system must:
- store corrected values  
- store OCR output  
- store confidence scores  
- store pre‑processed image  
- feed corrections into future OCR tuning (Phase 2)  

Corrections do **not** modify the OCR engine directly, but they inform:
- threshold adjustments  
- pre‑processing improvements  
- future model training  

---

# 12. Output of Matching Engine

The matching engine outputs:

```
{
  "match_status": "auto" | "tentative" | "needs_review",
  "selected_competitor_id": "<id or null>",
  "reason": "<string>",
  "number_used": "<string>",
  "class_used": "<string or null>",
  "confidence_number": <float>,
  "confidence_class": <float>
}
```

---

# 13. Summary

This Matching Policy ensures that RaceWrangler:

- prioritizes number over class  
- preserves leading zeros  
- handles stacked or improvised class letters  
- tolerates multiple class systems  
- avoids guessing  
- escalates ambiguity to Timing Staff  
- produces deterministic, explainable results  

This document completes the OCR specification set required for Copilot to generate a reliable OCR pipeline.

