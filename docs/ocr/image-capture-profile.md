# Image Capture Profile  
## RaceWrangler – OCR Input Characteristics  
## Version: April 2026

This document defines the expected visual characteristics of images used for OCR of car numbers and class letters in RaceWrangler.  
It provides Copilot with the constraints required to build a robust pre‑processing pipeline and to avoid incorrect assumptions about image quality, placement, or consistency.

---

# 1. Purpose

The goal of this profile is to describe the **real-world conditions** under which car numbers and class letters are photographed at autocross and time trial events.

This includes:
- camera placement  
- angles and distances  
- lighting conditions  
- motion blur  
- number/class placement variability  
- material and contrast variability  
- environmental factors  

OCR must be resilient to these conditions.

---

# 2. Camera Hardware & Settings

## 2.1 Expected Hardware
- Raspberry Pi camera modules (HQ Camera or equivalent)
- Fixed-focus lenses (6mm–16mm typical)
- Mounted on tripods, cones, or timing stands

## 2.2 Expected Resolution
- Minimum: **1280×720**
- Typical: **1920×1080**
- Higher resolutions allowed if performance permits

## 2.3 Expected Shutter Behavior
- Outdoor daylight: fast shutter, minimal blur  
- Overcast or shaded: moderate blur possible  
- Late afternoon: increased noise and blur  

## 2.4 Expected Frame Characteristics
- Single-frame still images (not video)
- JPEG or PNG format
- Variable compression levels

---

# 3. Camera Angle & Distance

## 3.1 Distance to Car
- Typical: **10–25 feet**
- Minimum: **6 feet**
- Maximum: **40 feet**

## 3.2 Angle of View
- Horizontal angle: **0–60°** off-axis  
- Vertical angle: **0–30°** above or below centerline  

## 3.3 Panel Curvature Effects
- Numbers may appear curved or warped due to door curvature  
- Class letters may be placed on fenders, doors, or rear quarter panels  

OCR must tolerate:
- perspective distortion  
- skew  
- curvature  
- foreshortening  

---

# 4. Lighting Conditions

## 4.1 Outdoor Lighting Variability
- Direct sunlight  
- Harsh shadows  
- Overcast diffuse lighting  
- Backlit cars  
- Reflective glare from glossy vinyl  
- Low-angle morning/evening sun  

## 4.2 Environmental Effects
- Dust  
- Water droplets  
- Mud splatter  
- Lens flare  
- Heat shimmer (rare but possible)

OCR must tolerate:
- high dynamic range  
- low contrast  
- glare hotspots  
- shadowed digits  
- uneven illumination  

---

# 5. Motion & Blur Characteristics

## 5.1 Expected Motion Blur
- Cars may be moving **5–40 mph** at the capture point  
- Blur may affect:
  - edges of digits  
  - taped class letters  
  - thin-stroke fonts  

## 5.2 Acceptable Blur Tolerance
OCR must handle:
- slight horizontal blur  
- slight vertical blur  
- slight rotational blur  

OCR may fail on:
- extreme blur  
- double-exposure blur  
- smear from slow shutter speeds  

---

# 6. Number & Class Placement Variability

## 6.1 Number Placement
Numbers may appear:
- on driver door  
- on passenger door  
- on rear quarter panel  
- on hood (rare)  
- on windows (rare but possible)  
- in multiple locations simultaneously  

OCR must not assume:
- consistent placement  
- consistent orientation  
- consistent proximity to class letters  

## 6.2 Class Letter Placement
Class letters may be:
- beside the number  
- above the number  
- below the number  
- far from the number  
- on a different panel entirely  

## 6.3 Class Letter Size Variability
Although SCCA recommends class letters be half the size of the number, in practice:

Class letters may be:
- **smaller than the number**  
- **equal in size**  
- **larger than the number**  
- **stacked vertically** (e.g., `"ST"` above `"X"`)  
- **taped on**, crooked, or improvised  
- **permanent TT class above temporary AX class**  
- **modified** with extra taped on characters

OCR must treat class letters as an **independent detection target**.

---

# 7. Material & Contrast Variability

## 7.1 Number Materials
Numbers may be:
- printed vinyl  
- magnetic panels  
- painter’s tape  
- duct tape  
- paper signs  
- hand-drawn markers  

## 7.2 Class Letter Materials
Class letters may be:
- vinyl  
- tape  
- marker  
- mixed materials  

## 7.3 Contrast Variability
Contrast may range from:
- high contrast (black on white)  
- medium contrast (blue on silver)  
- low contrast (yellow on white, gray on silver)  

OCR must tolerate:
- inconsistent stroke width  
- inconsistent edge sharpness  
- inconsistent color saturation  

---

# 8. Multiple Class Systems

Some competitors display:
- **permanent Time Trials class** (e.g., `"T3"`)  
- **temporary Autocross class** (e.g., `"STX"`)  
- **modifier letters** (e.g., `"L"` for Ladies)  
- **stacked or adjacent class blocks**  

OCR must:
- detect all class-like regions  
- return multiple candidates if needed  
- allow matching logic to decide which class applies  

---

# 9. Occlusion & Interference

OCR must tolerate:
- partial occlusion by door seams  
- shadows from mirrors  
- reflections from chrome trim  
- tape peeling or curling  
- digits partially cut off by camera framing  

---

# 10. Output Requirements

The pre-processing pipeline must produce:
- deskewed  
- contrast-normalized  
- thresholded  
- cropped  
- noise-reduced  

images suitable for OCR engines.

Intermediate images should be saved for debugging.

---

# 11. Summary

This Image Capture Profile defines the real-world conditions under which RaceWrangler captures images for OCR.  
It ensures that the OCR pipeline is designed for **actual competitor behavior**, not idealized rulebook conditions.

OCR must tolerate:
- inconsistent placement  
- inconsistent size  
- inconsistent materials  
- stacked classes  
- taped letters  
- multiple class systems  
- motion blur  
- glare  
- shadows  
- panel curvature  

This profile provides Copilot with the constraints needed to generate robust pre-processing and OCR code.

