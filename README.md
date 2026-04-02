# Race Wrangler
A modern, local‑first, camera‑driven timing and scoring system for autocross, time trials, hill climbs, and similar timed motorsports. Race Wrangler is designed around real‑world event workflows, volunteer‑friendly operation, and deterministic timing accuracy.

Race Wrangler embraces the natural variability of motorsports events rather than enforcing rigid structures like run order. It integrates timing cameras, OCR, validation, and lightweight Number Mistake Detection to deliver a reliable, extensible timing platform.

---

## Features

### 🕒 Deterministic Timing
- Raspberry Pi–class timing cameras
- Microsecond‑accurate timestamps
- Independent of network latency

### 🔍 Hybrid OCR Pipeline
- Lightweight pre‑processing on timing devices
- Server‑side OCR for car numbers and class letters
- Automatic run association with manual override tools

### ✔ Validation Pipeline
- Number readability checks  
- Class/run group correctness  
- Number Mistake Detection (Phase Two)  
- Starter‑reviewed final checks before each run

### 🚦 Real‑World Event Flow
Race Wrangler reflects the actual physical flow of events:

**Grid → Staging (Starter) → Start Line → Course → Finish → Grid**

- No run order required  
- Grid workers manage flow and communicate reruns  
- Starter performs final checks before releasing each car  

### 🧑‍🤝‍🧑 Volunteer‑Friendly Interfaces
- Role‑specific browser UIs  
- No accounts required for workers  
- Event‑scoped tokens for access  
- Simple, intuitive workflows  

### 🛠 Local‑First Architecture
- All critical operations run on a local server  
- Optional cloud sync for results and competitor profiles  

---

## Documentation
All project documentation is located in the `/docs/` directory:

- Product Vision  
- System Overview / ConOps  
- Stakeholder & User Roles  
- Feature Overview  
- High‑Level Architecture  

Additional documents (data model, timing protocol, UI wireframes) will be added as the project evolves.

---

## Project Status
This repository currently contains the foundational documentation and architectural direction for Race Wrangler. Implementation of the timing engine, OCR pipeline, worker interfaces, and hardware integration will follow.

---

## Contributing
Contributions are welcome once the core architecture stabilizes. Please see `CONTRIBUTING.md` (to be added) for guidelines.

---

## License
See the `LICENSE` file for details.