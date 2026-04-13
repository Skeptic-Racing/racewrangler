# Race Wrangler POC - Testing Workflow

## Quick Testing Checklist

### 1. STARTUP

#### Option A: Local Development
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
python app.py
# Expected: "✓ Database initialized and seeded" + "Uvicorn running on http://0.0.0.0:8000"

# Terminal 2 - Frontend  
cd frontend
npm run dev
# Expected: "VITE v5.x.x ready in XXXms" + "Local: http://localhost:3000"
```

#### Option B: Docker
```bash
docker-compose up
# Expected: Both services start and frontend ready on http://localhost:3000
```

### 2. VERIFY API

Open http://localhost:8000/docs in browser
- Should see FastAPI interactive docs
- Try "GET /api/cars" - should return 5 cars with numbers 1, 488, 911, 22, 66

### 3. VERIFY UI

Open http://localhost:3000 in browser
- Header shows "🏁 Race Wrangler POC"
- Three tabs visible: "👤 Starter UI", "🏁 Finish Worker UI", "⏱️ Timing & Scoring"
- Starter UI loaded by default

---

## WORKFLOW TESTING

### Step 1: START A RUN (Starter UI)

1. Tab: **Starter UI** ✓
2. **Search** for a car:
   - Type "1" → Should show "#1 - Audi R18 e-tron quattro (LMP1)"
   - OR type "ferrari" → Should show "#488 - Ferrari 488 GT3 (GT3)"
   - Select a car from dropdown
3. **Camera permission** - Allow browser access when prompted
4. **Take Photo** - Click "📸 Take Photo" button
   - Video feed should show (or black if no camera)
   - Preview image appears below button
5. **Confirm Start** - Click "✓ Confirm Start"
   - Success toast: "✓ Run #1 started for car #1"
   - UI should auto-advance to Finish Worker UI (optional)
   - Green checkmark appears next to car selection

### Step 2: CONFIRM FINISH (Finish Worker UI)

1. Tab: **Finish Worker UI** ✓
2. **Simulate Finish Trigger** - Click button
   - Button turns red: "🔴 FINISH TRIGGER DETECTED!"
   - Yellow alert box appears
3. **Select Car Photo** - Click the car photo from grid
   - Photo gets green border and checkmark
   - Photo cell highlights
4. **Confirm Finish** - Click "✓ Confirm Finish"
   - Success toast: "✓ Run #1 finished (X.XXXs)"
   - Should auto-advance to Timing UI
   - Run disappears from finish worker grid

### Step 3: MANAGE PENALTIES (Timing & Scoring UI)

1. Tab: **Timing & Scoring** ✓
2. **View Run** - Should see run in table
   - Columns: Photo, #, Class, Start Time, Finish Time, Raw Time, Penalties, Adjusted Time, Status, Actions
   - Car number displays (e.g., "1")
   - Status badge shows "Completed" (green)
   - Raw time shows (e.g., "6.123")
   - Adjusted time matches raw time (no penalties yet)

3. **Add Penalties** - Click "+1 Cone"
   - Penalties column increments to "1"
   - Adjusted time increases by 2.0 seconds (e.g., 6.123 → 8.123)

4. **Add More** - Click "+2 Cones"
   - Penalties: "3" (1 + 2)
   - Adjusted time should be raw_time + (3 × 2.0) = raw_time + 6.0

5. **Clear** - Click "✕" (clear button)
   - Penalties reset to "0"
   - Adjusted time equals raw time

6. **Toggle DNF** - Click "DNF"
   - Button turns red: "✓ DNF"
   - Status badge changes to "DNF" (orange)

7. **Toggle Abort** - Click "Abort"
   - Button turns red: "✓ Aborted"
   - Status badge changes to "Aborted" (red)

---

## VERIFICATION CHECKLIST

### Backend API
- [ ] `http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `http://localhost:8000/docs` shows OpenAPI interface
- [ ] `GET /api/cars` returns array of 5 cars
- [ ] `POST /api/start` with form data (car_id=1, photo=file) creates run
- [ ] `GET /api/runs` returns runs list
- [ ] Photos saved to `./storage/photos/start/` and `./storage/photos/finish/`

### Frontend Build
- [ ] `npm run build` completes without errors
- [ ] `dist/` folder contains `index.html`, CSS, JS
- [ ] Build size ~57KB (gzipped)
- [ ] `npm run dev` starts on http://localhost:3000

### Database
- [ ] `./backend/race_wrangler.db` exists (~28KB)
- [ ] Contains `cars` table with 5 rows
- [ ] Contains `runs` table (empty initially)
- [ ] Tables schema matches models.py definitions

### UI Functionality
- [ ] Starter UI: Searchable dropdown, camera feed, photo capture
- [ ] Finish Worker UI: Trigger button, photo grid, confirm button
- [ ] Timing UI: Auto-refreshing table, penalty buttons, search by #
- [ ] Toast notifications appear and auto-dismiss
- [ ] Tab navigation switches UIs
- [ ] All buttons disable appropriately while loading

---

## TROUBLESHOOTING

**Backend won't start**
```bash
cd backend
rm -f race_wrangler.db  # Reset DB
source venv/bin/activate
python app.py
```

**Frontend won't start**
```bash
cd frontend
rm -rf node_modules dist
npm install
npm run dev
```

**API not responding**
- Check backend console for errors
- Verify API docs at http://localhost:8000/docs
- Check CORS is enabled (should be in app.py)

**Camera not working**
- Grant browser permission when prompted
- Try different browser (Chrome recommended)
- Try HTTPS or localhost only

**Docker issues**
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

**Database errors**
- Check `./backend/race_wrangler.db` exists
- Try resetting: `rm -f ./backend/race_wrangler.db && python app.py`
- Verify seed data: `docs/poc/hardcoded cars list.json`

---

## STRESS TEST (Optional)

1. **Multiple Runs**: Create 5-10 runs rapidly (cycle through cars)
2. **Penalties**: Add various penalties to each run
3. **Status Changes**: Toggle DNF/Abort on different runs
4. **Concurrent Views**: Keep Timing UI open while starting new runs
5. **Auto-Refresh**: Timing UI should update every 1.5 seconds

---

## SUCCESS CRITERIA

✅ **POC Successful If:**
- Starter can start a run with photo
- Finish worker can confirm finish
- Timing staff can manage penalties/DNF/abort  
- All times compute correctly (raw + penalties × 2)
- Photos save and display correctly
- UI is responsive and intuitive
- No console errors
- Toast notifications provide feedback

💡 **This demonstrates the human-in-loop timing workflow that Race Wrangler enables!**
