const API_BASE_URL = (import.meta as any).env.VITE_API_URL || "/api";
const V1_BASE = "/api/v1";

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: { code: string; message: string };
}

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  const body: ApiResponse<T> = await res.json();
  if (!body.success) throw new Error(body.error?.message || "API error");
  return body.data as T;
}

// ---------------------------------------------------------------------------
// Phase 0 types (existing POC)
// ---------------------------------------------------------------------------

export interface Car {
  id: number;
  number: string;
  class_name: string;
  model: string;
}

export interface Run {
  id: number;
  car_id: number;
  start_time: string;
  finish_time?: string | null;
  raw_time?: number | null;
  start_photo_url?: string | null;
  finish_photo_url?: string | null;
  penalties: number;
  adjusted_time?: number | null;
  is_dnf: boolean;
  is_aborted: boolean;
  is_missed_trip: boolean;
  finish_confirmed: boolean;
  car?: Car;
}

export interface ResetDataResult { runs_deleted: number; photos_deleted: number; }
export interface ReleaseStartResult { is_start_held: boolean; }
export interface HoldStatusResult { is_start_held: boolean; }
export interface FinishTriggerStatusResult { is_finish_triggered: boolean; finish_triggered_at: string | null; }

// ---------------------------------------------------------------------------
// Phase 1 types
// ---------------------------------------------------------------------------

export interface Event {
  id: string;
  name: string;
  date: string | null;
  status: 'setup' | 'active' | 'complete';
  timing_mode: 'human' | 'racespy';
  created_at: string;
}

export interface RunGroup {
  id: string;
  event_id: string;
  name: string;
  order: number;
  competitor_count: number;
}

export interface Competitor {
  id: string;
  event_id: string;
  number: string;
  class_code: string;
  driver_name: string;
  car_description: string | null;
  run_group_id: string | null;
  run_group_name: string | null;
}

export interface ClassSummary {
  class_code: string;
  competitor_count: number;
  assigned_group_id: string | null;
  split: boolean;
}

export interface Camera {
  id: string;
  event_id: string | null;
  role: string | null;
  status: string;
  firmware_version: string | null;
  last_seen_at: string | null;
}

export interface TimingEventItem {
  id: string;
  camera_id: string;
  role: string;
  timestamp_utc_ms: number;
  match_status: string | null;
  matched_competitor_id: string | null;
  image_path: string | null;
  ocr_detail: any;
  suggested_competitor: Competitor | null;
}

export interface StagedRun {
  id: string;
  event_id: string;
  status: 'staged' | 'running' | 'finished' | 'dnf';
  competitor: {
    id: string;
    number: string;
    class_code: string;
    driver_name: string;
    car_description: string | null;
  } | null;
  start_time_utc_ms: number | null;
  finish_time_utc_ms: number | null;
  raw_time_s: number | null;
  adjusted_time_s: number | null;
  penalties: number;
  image_path: string | null;
  staged_at: string;
}

export interface OCRScanResult {
  match_status: string;
  matched_competitor_id: string | null;
  candidates: Array<{
    competitor_id: string;
    number: string;
    class_code: string;
    driver_name: string;
    car_description: string | null;
    confidence?: number;
  }>;
  raw_text: string | null;
}

// ---------------------------------------------------------------------------
// Phase 0 API (existing POC — unchanged)
// ---------------------------------------------------------------------------

export async function getCars(): Promise<Car[]> {
  const res = await fetch(`${API_BASE_URL}/cars`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function startRun(car_id: number, photo: File): Promise<Run> {
  const fd = new FormData();
  fd.append("car_id", car_id.toString());
  fd.append("photo", photo);
  return apiFetch<Run>(`${API_BASE_URL}/start`, { method: "POST", body: fd });
}

export async function finishRun(run_id: number, photo: File): Promise<Run> {
  const fd = new FormData();
  fd.append("run_id", run_id.toString());
  fd.append("photo", photo);
  return apiFetch<Run>(`${API_BASE_URL}/finish`, { method: "POST", body: fd });
}

export async function getRuns(status?: string): Promise<Run[]> {
  const url = status ? `${API_BASE_URL}/runs?status=${status}` : `${API_BASE_URL}/runs`;
  const d = await apiFetch<{ runs: Run[] }>(url);
  return d.runs;
}

export async function updateRun(run_id: number, update: { penalties?: number; is_dnf?: boolean; is_aborted?: boolean; is_missed_trip?: boolean }): Promise<Run> {
  return apiFetch<Run>(`${API_BASE_URL}/runs/${run_id}/update`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(update) });
}

export async function resetData(): Promise<ResetDataResult> {
  return apiFetch<ResetDataResult>(`${API_BASE_URL}/admin/reset`, { method: "POST" });
}

export async function deleteRun(run_id: number): Promise<void> {
  await apiFetch(`${API_BASE_URL}/runs/${run_id}`, { method: "DELETE" });
}

export async function releaseStart(): Promise<ReleaseStartResult> {
  return apiFetch<ReleaseStartResult>(`${API_BASE_URL}/runs/release-start`, { method: "POST" });
}

export async function holdStart(): Promise<HoldStatusResult> {
  return apiFetch<HoldStatusResult>(`${API_BASE_URL}/runs/hold-start`, { method: "POST" });
}

export async function getHoldStatus(): Promise<HoldStatusResult> {
  return apiFetch<HoldStatusResult>(`${API_BASE_URL}/runs/hold-status`);
}

export async function triggerFinish(): Promise<FinishTriggerStatusResult> {
  return apiFetch<FinishTriggerStatusResult>(`${API_BASE_URL}/runs/trigger-finish`, { method: "POST" });
}

export async function getFinishTriggerStatus(): Promise<FinishTriggerStatusResult> {
  return apiFetch<FinishTriggerStatusResult>(`${API_BASE_URL}/runs/finish-trigger-status`);
}

// ---------------------------------------------------------------------------
// Phase 1 — Events
// ---------------------------------------------------------------------------

export async function listEvents(): Promise<Event[]> {
  const d = await apiFetch<{ events: Event[] }>(`${V1_BASE}/events`);
  return d.events;
}

export async function createEvent(name: string, date: string | null, timing_mode: 'human' | 'racespy'): Promise<Event> {
  return apiFetch<Event>(`${V1_BASE}/events`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, date, timing_mode }) });
}

export async function updateEvent(event_id: string, patch: Partial<Pick<Event, 'name' | 'status' | 'timing_mode'>>): Promise<Event> {
  return apiFetch<Event>(`${V1_BASE}/events/${event_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
}

// ---------------------------------------------------------------------------
// Phase 1 — Run Groups
// ---------------------------------------------------------------------------

export async function listRunGroups(event_id: string): Promise<RunGroup[]> {
  const d = await apiFetch<{ run_groups: RunGroup[] }>(`${V1_BASE}/events/${event_id}/run-groups`);
  return d.run_groups;
}

export async function createRunGroup(event_id: string, name: string, order?: number): Promise<RunGroup> {
  return apiFetch<RunGroup>(`${V1_BASE}/events/${event_id}/run-groups`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, order }) });
}

export async function deleteRunGroup(event_id: string, group_id: string): Promise<void> {
  await apiFetch(`${V1_BASE}/events/${event_id}/run-groups/${group_id}`, { method: "DELETE" });
}

export async function getAssignmentSummary(event_id: string): Promise<ClassSummary[]> {
  const d = await apiFetch<{ classes: ClassSummary[] }>(`${V1_BASE}/events/${event_id}/run-groups/assignment-summary`);
  return d.classes;
}

export async function bulkAssign(event_id: string, assignments: Array<{ class_code: string; run_group_id: string }>): Promise<{ competitors_updated: number }> {
  return apiFetch(`${V1_BASE}/events/${event_id}/run-groups/bulk-assign`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ assignments }) });
}

// ---------------------------------------------------------------------------
// Phase 1 — Competitors
// ---------------------------------------------------------------------------

export async function listCompetitors(event_id: string, run_group_id?: string): Promise<Competitor[]> {
  const url = run_group_id
    ? `${V1_BASE}/events/${event_id}/competitors?run_group_id=${run_group_id}`
    : `${V1_BASE}/events/${event_id}/competitors`;
  const d = await apiFetch<{ competitors: Competitor[] }>(url);
  return d.competitors;
}

export async function importCompetitorsCSV(event_id: string, file: File): Promise<{ imported: number; skipped: number; errors: string[] }> {
  const fd = new FormData();
  fd.append("file", file);
  return apiFetch(`${V1_BASE}/events/${event_id}/competitors/import`, { method: "POST", body: fd });
}

export async function updateCompetitor(event_id: string, competitor_id: string, patch: { run_group_id?: string | null }): Promise<Competitor> {
  return apiFetch<Competitor>(`${V1_BASE}/events/${event_id}/competitors/${competitor_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
}

// ---------------------------------------------------------------------------
// Phase 1 — Cameras
// ---------------------------------------------------------------------------

export async function listCameras(): Promise<Camera[]> {
  const d = await apiFetch<{ cameras: Camera[] }>(`/api/cameras`);
  return d.cameras;
}

// ---------------------------------------------------------------------------
// Phase 1 — Ambiguity Queue
// ---------------------------------------------------------------------------

export async function getAmbiguityCount(event_id: string): Promise<number> {
  const d = await apiFetch<{ pending: number }>(`${V1_BASE}/events/${event_id}/ambiguity-queue/count`);
  return d.pending;
}

export async function getAmbiguityQueue(event_id: string): Promise<TimingEventItem[]> {
  const d = await apiFetch<{ queue: TimingEventItem[] }>(`${V1_BASE}/events/${event_id}/ambiguity-queue`);
  return d.queue;
}

export async function resolveAmbiguity(event_id: string, timing_event_id: string, action: 'select' | 'skip' | 'unknown', competitor_id?: string): Promise<void> {
  await apiFetch(`${V1_BASE}/events/${event_id}/ambiguity-queue/${timing_event_id}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, competitor_id }),
  });
}

// ---------------------------------------------------------------------------
// Phase 1 — Staged Runs
// ---------------------------------------------------------------------------

export async function ocrScan(event_id: string, image_base64: string): Promise<OCRScanResult> {
  return apiFetch<OCRScanResult>(`${V1_BASE}/events/${event_id}/staged-runs/ocr-scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_base64 }),
  });
}

export async function createStagedRun(event_id: string, competitor_id: string, image_base64?: string): Promise<StagedRun> {
  return apiFetch<StagedRun>(`${V1_BASE}/events/${event_id}/staged-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ competitor_id, image_base64 }),
  });
}

export async function listStagedRuns(event_id: string, status?: string): Promise<StagedRun[]> {
  const url = status
    ? `${V1_BASE}/events/${event_id}/staged-runs?status=${status}`
    : `${V1_BASE}/events/${event_id}/staged-runs`;
  const d = await apiFetch<{ staged_runs: StagedRun[] }>(url);
  return d.staged_runs;
}

export async function setStagedRunPenalties(event_id: string, run_id: string, penalties: number): Promise<StagedRun> {
  return apiFetch<StagedRun>(`${V1_BASE}/events/${event_id}/staged-runs/${run_id}/penalties`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ penalties }),
  });
}

export async function markStagedRunDNF(event_id: string, run_id: string): Promise<StagedRun> {
  return apiFetch<StagedRun>(`${V1_BASE}/events/${event_id}/staged-runs/${run_id}/dnf`, { method: "POST" });
}

export async function deleteStagedRun(event_id: string, run_id: string): Promise<void> {
  await apiFetch(`${V1_BASE}/events/${event_id}/staged-runs/${run_id}`, { method: "DELETE" });
}
