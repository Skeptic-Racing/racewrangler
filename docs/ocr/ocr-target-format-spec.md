# OCR Target Format Specification  
## RaceWrangler – Number & Class Recognition  

This document defines the exact formats, normalization rules, and constraints for OCR extraction of **car numbers** and **class letters** in RaceWrangler.  
It ensures deterministic behavior in the OCR pipeline and prevents Copilot from guessing or hallucinating formats.

---

# 1. Overview

RaceWrangler OCR must extract two independent fields:

1. **Car Number** — a numeric identifier (1–4 digits), where **leading zeros are meaningful**  
2. **Class Letters** — an alphanumeric SCCA-style class code (1–4 characters)

These fields may appear together or separately on the car body.  
OCR must treat them as **independent targets**.

---

# 2. Car Number Format

## 2.1 Allowed Characters
- Digits: `0–9` only  
- No letters  
- No punctuation  
- No symbols  

## 2.2 Length
- Minimum: **1 digit**  
- Maximum: **4 digits**  
- Typical: 2–3 digits  

## 2.3 Leading Zeros
- **Leading zeros are meaningful and must be preserved**  
- `"01"` and `"1"` are treated as **different competitor numbers**  
- `"007"` and `"7"` are **not equivalent**

## 2.4 Valid Examples

```
7
01
042
318
0001
```

## 2.5 Invalid Examples

```
A12
12B
1-2
```

---

# 3. Class Letter Format

## 3.1 Allowed Characters
- Uppercase letters: `A–Z`
- Digits: `0–9` (for classes like “STX”, “CAM-C”, “SMF”)
- Hyphen: `-` (only as separator in multi-part classes)

## 3.2 Length
- Minimum: **1 character**  
- Maximum: **4 characters** (after normalization)

## 3.3 Case Normalization
- OCR output is normalized to **uppercase**  
  - Example: `"stx"` → `"STX"`

## 3.4 Hyphen Normalization
- Hyphens are **optional** in OCR output  
- System normalizes both:
  - `"CAMC"` → `"CAM-C"`
  - `"CAM-C"` → `"CAM-C"`

## 3.5 Valid Examples

```
SS
AS
STX
STR
SMF
CAM-C
CAM-S
CAM-T
```

## 3.6 Invalid Examples

```
stx  (lowercase → normalized to STX)
CAM C (space not allowed)
C@M (symbols not allowed)
```

---

# 4. Combined Number + Class Layouts

Numbers and class letters may appear:

- **Side-by-side** (e.g., `"318 STX"`)
- **Stacked vertically**
- **Separated on different panels**
- **Different sizes**
- **Different fonts**
- **Different colors**

OCR must treat number and class as **independent detection targets**.

OCR must **not** assume:
- ordering  
- proximity  
- relative size  
- consistent font  
- consistent color  

## 4.1 Real‑World Class Marking Variability

In practice, competitors may display class letters in inconsistent or non‑standard ways.  
OCR must tolerate the following variations:

- Class letters may be **smaller, equal, or larger** than the car number  
- Class letters may be **stacked vertically** (e.g., `"ST"` above `"X"`)  
- Class letters may be **taped**, partially hand‑drawn, or improvised  
- Class letters may be **crooked**, skewed, or misaligned  
- Class letters may appear in **multiple locations** on the car  
- Competitors may display **multiple classes simultaneously**  
  - Example: a permanent Time Trials class above a temporary Autocross class  
- Class letters may be **adjacent to**, **far from**, or **completely separate** from the number  
- Class letters may be **different colors** or **different fonts** than the number  
- Class letters may be **partially occluded** by door seams, shadows, or tape

OCR must treat class letters as an **independent detection target** and must not assume:
- relative size  
- relative position  
- consistent font  
- consistent color  
- consistent orientation  
- consistent grouping  

---

# 5. Normalization Rules

After OCR extraction:

1. Strip whitespace  
2. Convert class letters to uppercase  
3. **Preserve leading zeros in car numbers**  
4. Normalize hyphens in class codes  
5. Reject any characters outside allowed sets  

---

# 6. Ambiguity Handling

If OCR returns ambiguous results:

- Prefer **pure numeric** candidates for car number  
- Prefer **pure alphabetic or alphanumeric** candidates for class  
- Reject candidates containing mixed letters/digits for number  
- Reject candidates containing symbols (except hyphen for class)  
- **Do not strip or alter leading zeros**  

---

# 7. Output Format

OCR pipeline must output a JSON object:

```
{
  "number_raw": "<string>",
  "number_normalized": "<string>",   // identical to raw; leading zeros preserved
  "class_raw": "<string>",
  "class_normalized": "<string>",
  "confidence_number": <0.0–1.0>,
  "confidence_class": <0.0–1.0>
}
```

Fields may be `null` if unreadable.

---

# 8. Non-Goals

OCR does **not** attempt to:
- detect the car body  
- detect bounding boxes for numbers/classes  
- detect sponsor decals  
- detect windshield banners  
- detect helmet numbers  
- detect license plates  

OCR is strictly for **race numbers** and **class letters**.

---

# 9. Summary

This specification defines the exact formats and normalization rules for OCR extraction of car numbers and class letters.

