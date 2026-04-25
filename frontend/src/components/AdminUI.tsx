import { useState, useEffect, useRef } from 'react';
import {
  listEvents, createEvent, updateEvent, startEvent, endEvent,
  listRunGroups, createRunGroup, deleteRunGroup, startRunGroup, stopRunGroup,
  getAssignmentSummary, bulkAssign,
  listCompetitors, updateCompetitor, importCompetitorsCSV,
  listCameras, listCameraTelemetry, assignCamera, resetCamera, cameraPreviewUrl, resetData,
  type Event, type RunGroup, type Competitor, type ClassSummary, type Camera, type CameraTelemetrySnapshot,
} from '../services/api';

interface AdminUIProps {
  activeEvent: Event | null;
  onEventChange: (event: Event | null) => void;
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}

type AdminTab = 'event' | 'groups' | 'competitors' | 'cameras' | 'reset';

const btn = (extra: React.CSSProperties = {}): React.CSSProperties => ({
  padding: '6px 14px', cursor: 'pointer', borderRadius: 4, border: 'none', fontSize: 13, ...extra,
});

export function AdminUI({ activeEvent, onEventChange, onError, onSuccess }: AdminUIProps) {
  const [tab, setTab] = useState<AdminTab>('event');
  const [events, setEvents] = useState<Event[]>([]);
  const [runGroups, setRunGroups] = useState<RunGroup[]>([]);
  const [classSummary, setClassSummary] = useState<ClassSummary[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [telemetryByCamera, setTelemetryByCamera] = useState<Record<string, CameraTelemetrySnapshot>>({});

  // Event creation
  const [newEventName, setNewEventName] = useState('');
  const [newEventDate, setNewEventDate] = useState('');
  const [newEventMode, setNewEventMode] = useState<'human' | 'racespy'>('human');
  const [creatingEvent, setCreatingEvent] = useState(false);

  // Run group
  const [newGroupName, setNewGroupName] = useState('');
  // drag state: which class_code is being dragged
  const [dragClass, setDragClass] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null); // group id or 'unassigned'

  // Camera
  const [camRoles, setCamRoles] = useState<Record<string, 'start' | 'finish'>>({});
  const [camEvents, setCamEvents] = useState<Record<string, string>>({});
  const [assigning, setAssigning] = useState<string | null>(null);

  // CSV
  const csvRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  // Reset
  const [confirmReset, setConfirmReset] = useState(false);

  useEffect(() => { loadEvents(); }, []);
  useEffect(() => {
    if (!activeEvent) return;
    if (tab === 'groups') { loadGroupsAndSummary(); }
    if (tab === 'competitors') { loadGroupsAndSummary(); loadCompetitors(); }
  }, [activeEvent, tab]);

  useEffect(() => {
    if (tab !== 'cameras') return;
    loadCameras();
    const interval = setInterval(loadCameras, 5000);
    return () => clearInterval(interval);
  }, [tab, activeEvent?.id]);

  async function loadEvents() {
    try { setEvents(await listEvents()); } catch (e) { onError(`${e}`); }
  }

  async function loadGroupsAndSummary() {
    if (!activeEvent) return;
    try {
      const [groups, summary] = await Promise.all([
        listRunGroups(activeEvent.id),
        getAssignmentSummary(activeEvent.id),
      ]);
      setRunGroups(groups);
      setClassSummary(summary);
    } catch (e) { onError(`${e}`); }
  }

  async function loadCompetitors() {
    if (!activeEvent) return;
    try { setCompetitors(await listCompetitors(activeEvent.id)); } catch (e) { onError(`${e}`); }
  }

  async function loadCameras() {
    try {
      const [cameraList, telemetry] = await Promise.all([
        listCameras(),
        listCameraTelemetry(activeEvent?.id),
      ]);
      setCameras(cameraList);
      const mapped: Record<string, CameraTelemetrySnapshot> = {};
      for (const t of telemetry) mapped[t.camera_id] = t;
      setTelemetryByCamera(mapped);
    } catch {}
  }

  // ── Event tab ──────────────────────────────────────────────────────────────

  async function handleCreateEvent() {
    if (!newEventName.trim()) return;
    setCreatingEvent(true);
    try {
      const ev = await createEvent(newEventName.trim(), newEventDate || null, newEventMode);
      onSuccess(`Event "${ev.name}" created`);
      setNewEventName(''); setNewEventDate('');
      await loadEvents();
      onEventChange(ev);
    } catch (e) { onError(`${e}`); }
    finally { setCreatingEvent(false); }
  }

  async function handleStartEvent(ev: Event) {
    try {
      const updated = await startEvent(ev.id);
      onEventChange(updated);
      onSuccess(`Event "${updated.name}" is now active`);
      await loadEvents();
    } catch (e) { onError(`${e}`); }
  }

  async function handleEndEvent(ev: Event) {
    try {
      const updated = await endEvent(ev.id);
      onEventChange(null);
      onSuccess(`Event "${updated.name}" ended`);
      await loadEvents();
    } catch (e) { onError(`${e}`); }
  }

  async function handleUpdateMode(mode: 'human' | 'racespy') {
    if (!activeEvent) return;
    try {
      const updated = await updateEvent(activeEvent.id, { timing_mode: mode });
      onEventChange(updated);
      onSuccess(`Timing mode set to ${mode}`);
    } catch (e) { onError(`${e}`); }
  }

  // ── Run groups tab ─────────────────────────────────────────────────────────

  async function handleCreateGroup() {
    if (!activeEvent || !newGroupName.trim()) return;
    try {
      await createRunGroup(activeEvent.id, newGroupName.trim(), runGroups.length);
      setNewGroupName('');
      await loadGroupsAndSummary();
    } catch (e) { onError(`${e}`); }
  }

  async function handleDeleteGroup(id: string) {
    if (!activeEvent) return;
    try {
      await deleteRunGroup(activeEvent.id, id);
      await loadGroupsAndSummary();
    } catch (e) { onError(`${e}`); }
  }

  async function handleStartRunGroup(groupId: string) {
    if (!activeEvent) return;
    try {
      const updated = await startRunGroup(activeEvent.id, groupId);
      onEventChange(updated);
      const group = runGroups.find(g => g.id === groupId);
      onSuccess(`Run group "${group?.name}" is now active for OCR`);
    } catch (e) { onError(`${e}`); }
  }

  async function handleStopRunGroup() {
    if (!activeEvent) return;
    try {
      const updated = await stopRunGroup(activeEvent.id);
      onEventChange(updated);
      onSuccess('Run group deactivated — OCR uses all competitors');
    } catch (e) { onError(`${e}`); }
  }

  // Drag-and-drop: drop a class onto a group bin
  async function handleDropOnGroup(groupId: string | null) {
    if (!activeEvent || !dragClass) return;
    setDragClass(null);
    setDragOver(null);
    try {
      const assignments = [{ class_code: dragClass, run_group_id: groupId ?? '' }];
      if (groupId) {
        await bulkAssign(activeEvent.id, assignments);
      } else {
        // Drop onto "Unassigned" — clear run_group_id for this class
        const toUpdate = competitors.filter(c => c.class_code === dragClass);
        await Promise.all(toUpdate.map(c => updateCompetitor(activeEvent.id, c.id, { run_group_id: null })));
      }
      await loadGroupsAndSummary();
    } catch (e) { onError(`${e}`); }
  }

  // ── Competitors tab ────────────────────────────────────────────────────────

  async function handleCSVImport(e: React.ChangeEvent<HTMLInputElement>) {
    if (!activeEvent || !e.target.files?.[0]) return;
    setImporting(true);
    try {
      const r = await importCompetitorsCSV(activeEvent.id, e.target.files[0]);
      onSuccess(`Imported ${r.imported} competitors (${r.skipped} skipped)`);
      if (r.errors.length) onError(`Import warnings: ${r.errors.slice(0, 3).join('; ')}`);
      await loadCompetitors();
    } catch (err) { onError(`Import failed: ${err}`); }
    finally { setImporting(false); if (csvRef.current) csvRef.current.value = ''; }
  }

  async function handleMoveCompetitor(comp: Competitor, run_group_id: string | null) {
    if (!activeEvent) return;
    try {
      await updateCompetitor(activeEvent.id, comp.id, { run_group_id });
      await loadCompetitors();
    } catch (e) { onError(`${e}`); }
  }

  // ── Cameras tab ────────────────────────────────────────────────────────────

  async function handleAssignCamera(camera_id: string) {
    const cam = cameras.find(c => c.camera_id === camera_id);
    const role = camRoles[camera_id] || (cam?.role as 'start' | 'finish' | null) || 'start';
    const event_id = camEvents[camera_id] || activeEvent?.id;
    if (!event_id) { onError('Select an event first'); return; }
    setAssigning(camera_id);
    try {
      await assignCamera(camera_id, role, event_id);
      onSuccess(`Camera ${camera_id.slice(0, 8)} assigned as ${role}`);
      await loadCameras();
    } catch (e) { onError(`${e}`); }
    finally { setAssigning(null); }
  }

  async function handleResetCamera(camera_id: string) {
    try {
      await resetCamera(camera_id);
      onSuccess(`Camera ${camera_id.slice(0, 8)} reset`);
      await loadCameras();
    } catch (e) { onError(`${e}`); }
  }

  // ── Reset tab ──────────────────────────────────────────────────────────────

  async function handleReset() {
    try {
      const r = await resetData();
      onSuccess(`Reset: ${r.runs_deleted} runs deleted`);
      setConfirmReset(false);
    } catch (e) { onError(`${e}`); }
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  const unassignedClasses = classSummary.filter(c => !c.assigned_group_id && !c.split);
  const dropZoneStyle = (id: string | null): React.CSSProperties => ({
    minHeight: 80, borderRadius: 6, padding: 8,
    border: `2px dashed ${dragOver === (id ?? 'unassigned') ? '#1a56db' : '#e5e7eb'}`,
    background: dragOver === (id ?? 'unassigned') ? '#eff6ff' : '#f9fafb',
    transition: 'all 0.15s',
  });

  function formatTelemetryAge(ageSeconds: number | null): string {
    if (ageSeconds == null) return 'no data';
    if (ageSeconds < 60) return `${Math.round(ageSeconds)}s ago`;
    const mins = Math.floor(ageSeconds / 60);
    const secs = Math.round(ageSeconds % 60);
    return `${mins}m ${secs}s ago`;
  }

  function formatUptime(seconds: number | null): string {
    if (seconds == null) return 'n/a';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  }

  const camerasWithTelemetry = cameras.filter(c => telemetryByCamera[c.camera_id]);
  const warningCameras = camerasWithTelemetry.filter(c => {
    const t = telemetryByCamera[c.camera_id];
    return t.stale || t.alerts.length > 0;
  }).length;

  function ClassCard({ cls }: { cls: ClassSummary }) {
    return (
      <div
        draggable
        onDragStart={() => setDragClass(cls.class_code)}
        onDragEnd={() => { setDragClass(null); setDragOver(null); }}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 10px', margin: '3px',
          background: dragClass === cls.class_code ? '#bfdbfe' : 'white',
          border: '1px solid #d1d5db', borderRadius: 20,
          cursor: 'grab', fontSize: 13, userSelect: 'none',
          boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
        }}
      >
        <strong>{cls.class_code}</strong>
        <span style={{ color: '#888', fontSize: 11 }}>{cls.competitor_count}</span>
        {cls.split && <span style={{ color: '#d97706', fontSize: 10 }}>⚠</span>}
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* Sub-navigation */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {(['event', 'groups', 'competitors', 'cameras', 'reset'] as AdminTab[]).map(t => (
          <button key={t} onClick={() => setTab(t)} style={btn({
            background: tab === t ? '#1a56db' : '#f3f4f6',
            color: tab === t ? 'white' : '#333',
          })}>
            {{ event: '📋 Event', groups: '👥 Run Groups', competitors: '🚗 Competitors', cameras: '📷 Cameras', reset: '⚠️ Reset' }[t]}
          </button>
        ))}
      </div>

      {/* ── EVENT ── */}
      {tab === 'event' && (
        <div className="card">
          <div className="card-header">Event Setup</div>
          <div style={{ padding: 16 }}>
            <h3 style={{ marginTop: 0 }}>Create New Event</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
              <input placeholder="Event name" value={newEventName} onChange={e => setNewEventName(e.target.value)}
                style={{ flex: 1, minWidth: 200, padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc' }} />
              <input type="date" value={newEventDate} onChange={e => setNewEventDate(e.target.value)}
                style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc' }} />
              <select value={newEventMode} onChange={e => setNewEventMode(e.target.value as any)}
                style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc' }}>
                <option value="human">Human timing</option>
                <option value="racespy">RaceSpy + Staging</option>
              </select>
              <button style={btn({ background: '#1a56db', color: 'white' })} onClick={handleCreateEvent} disabled={creatingEvent}>
                {creatingEvent ? 'Creating…' : 'Create Event'}
              </button>
            </div>

            <h3>Events</h3>
            {events.length === 0 && <p style={{ color: '#888' }}>No events yet.</p>}
            {events.map(ev => {
              const isActive = activeEvent?.id === ev.id;
              const isLive = ev.status === 'active';
              return (
                <div key={ev.id} style={{
                  padding: 12, border: `2px solid ${isActive ? '#1a56db' : '#e5e7eb'}`,
                  borderRadius: 6, marginBottom: 8, background: isActive ? '#eff6ff' : 'white',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div style={{ cursor: 'pointer' }} onClick={() => onEventChange(ev)}>
                    <strong>{ev.name}</strong>
                    <span style={{ marginLeft: 10, color: '#555', fontSize: 13 }}>{ev.date || 'No date'}</span>
                    <span style={{ marginLeft: 8, fontSize: 12, padding: '2px 8px', borderRadius: 12,
                      background: isLive ? '#def7ec' : '#f3f4f6', color: isLive ? '#03543f' : '#555' }}>
                      {ev.status}
                    </span>
                    <span style={{ marginLeft: 6, fontSize: 12, padding: '2px 8px', borderRadius: 12, background: '#fef3c7', color: '#92400e' }}>
                      {ev.timing_mode}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {!isLive && (
                      <button style={btn({ background: '#065f46', color: 'white' })} onClick={() => handleStartEvent(ev)}>
                        ▶ Start Event
                      </button>
                    )}
                    {isLive && (
                      <button style={btn({ background: '#c81e1e', color: 'white' })} onClick={() => handleEndEvent(ev)}>
                        ■ End Event
                      </button>
                    )}
                  </div>
                </div>
              );
            })}

            {activeEvent && (
              <div style={{ marginTop: 16, padding: 12, background: '#f9fafb', borderRadius: 6 }}>
                <strong>Timing mode for {activeEvent.name}:</strong>
                <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                  {(['human', 'racespy'] as const).map(m => (
                    <button key={m} style={btn({
                      background: activeEvent.timing_mode === m ? '#1a56db' : '#f3f4f6',
                      color: activeEvent.timing_mode === m ? 'white' : '#333',
                    })} onClick={() => handleUpdateMode(m)}>
                      {m === 'human' ? 'Human' : 'RaceSpy + Staging'}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── RUN GROUPS ── */}
      {tab === 'groups' && (
        <div className="card">
          <div className="card-header">Run Groups {activeEvent ? `— ${activeEvent.name}` : ''}</div>
          {!activeEvent ? <p style={{ padding: 16, color: '#888' }}>Select an event first.</p> : (
            <div style={{ padding: 16 }}>
              {/* Create group */}
              <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
                <input placeholder="New group name (e.g. Group 1)" value={newGroupName}
                  onChange={e => setNewGroupName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleCreateGroup()}
                  style={{ flex: 1, padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc' }} />
                <button style={btn({ background: '#1a56db', color: 'white' })} onClick={handleCreateGroup}>
                  + Add Group
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 16 }}>
                {/* Left: unassigned classes */}
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#555', marginBottom: 6 }}>
                    UNASSIGNED CLASSES
                  </div>
                  <div
                    style={dropZoneStyle(null)}
                    onDragOver={e => { e.preventDefault(); setDragOver('unassigned'); }}
                    onDragLeave={() => setDragOver(null)}
                    onDrop={() => handleDropOnGroup(null)}
                  >
                    {unassignedClasses.length === 0
                      ? <span style={{ color: '#aaa', fontSize: 12 }}>All classes assigned</span>
                      : unassignedClasses.map(c => <ClassCard key={c.class_code} cls={c} />)
                    }
                  </div>
                  {classSummary.filter(c => c.split).length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 12, color: '#d97706', marginBottom: 4 }}>⚠ Split across groups:</div>
                      {classSummary.filter(c => c.split).map(c => <ClassCard key={c.class_code} cls={c} />)}
                    </div>
                  )}
                  <p style={{ fontSize: 11, color: '#aaa', marginTop: 8 }}>Drag classes into groups →</p>
                </div>

                {/* Right: group bins */}
                <div>
                  {runGroups.length === 0 ? (
                    <div style={{ padding: 24, textAlign: 'center', color: '#888', border: '2px dashed #e5e7eb', borderRadius: 6 }}>
                      Add a run group to get started
                    </div>
                  ) : (
                    runGroups.map(group => {
                      const groupClasses = classSummary.filter(c => c.assigned_group_id === group.id);
                      const isActive = activeEvent?.active_run_group_id === group.id;
                      return (
                        <div key={group.id} style={{
                          marginBottom: 12, border: `2px solid ${isActive ? '#7c3aed' : '#e5e7eb'}`,
                          borderRadius: 8, overflow: 'hidden',
                        }}>
                          <div style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '8px 12px',
                            background: isActive ? '#f5f3ff' : '#f9fafb',
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <strong>{group.name}</strong>
                              <span style={{ fontSize: 12, color: '#888' }}>
                                ({group.competitor_count} competitors, {groupClasses.length} classes)
                              </span>
                              {isActive && (
                                <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 10, background: '#7c3aed', color: 'white' }}>
                                  ACTIVE
                                </span>
                              )}
                            </div>
                            <div style={{ display: 'flex', gap: 6 }}>
                              {isActive ? (
                                <button style={btn({ background: '#6b7280', color: 'white', fontSize: 12 })}
                                  onClick={handleStopRunGroup}>
                                  ■ Stop Group
                                </button>
                              ) : (
                                <button style={btn({ background: '#7c3aed', color: 'white', fontSize: 12 })}
                                  onClick={() => handleStartRunGroup(group.id)}>
                                  ▶ Start Group
                                </button>
                              )}
                              <button style={btn({ background: '#fee2e2', color: '#c81e1e', fontSize: 12 })}
                                onClick={() => handleDeleteGroup(group.id)}>
                                Delete
                              </button>
                            </div>
                          </div>
                          <div
                            style={{ ...dropZoneStyle(group.id), minHeight: 60, borderRadius: 0, border: 'none', borderTop: '1px dashed #e5e7eb' }}
                            onDragOver={e => { e.preventDefault(); setDragOver(group.id); }}
                            onDragLeave={() => setDragOver(null)}
                            onDrop={() => handleDropOnGroup(group.id)}
                          >
                            {groupClasses.length === 0
                              ? <span style={{ color: '#aaa', fontSize: 12 }}>Drop classes here</span>
                              : groupClasses.map(c => <ClassCard key={c.class_code} cls={c} />)
                            }
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── COMPETITORS ── */}
      {tab === 'competitors' && (
        <div className="card">
          <div className="card-header">Competitors {activeEvent ? `— ${activeEvent.name}` : ''}</div>
          {!activeEvent ? <p style={{ padding: 16, color: '#888' }}>Select an event first.</p> : (
            <div style={{ padding: 16 }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
                <label style={btn({ background: '#1a56db', color: 'white', cursor: 'pointer' })}>
                  {importing ? 'Importing…' : '📁 Import CSV (MotorsportsReg)'}
                  <input ref={csvRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleCSVImport} disabled={importing} />
                </label>
                <span style={{ color: '#888', fontSize: 13 }}>{competitors.length} competitors loaded</span>
              </div>
              {competitors.length === 0 ? (
                <p style={{ color: '#888' }}>No competitors yet. Upload a MotorsportsReg CSV export.</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#f3f4f6' }}>
                        {['#', 'Class', 'Driver', 'Car', 'Group'].map(h => (
                          <th key={h} style={{ padding: '6px 10px', textAlign: 'left' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {competitors.map(c => (
                        <tr key={c.id} style={{ borderTop: '1px solid #e5e7eb' }}>
                          <td style={{ padding: '6px 10px', fontWeight: 600 }}>{c.number}</td>
                          <td style={{ padding: '6px 10px' }}>{c.class_code}</td>
                          <td style={{ padding: '6px 10px' }}>{c.driver_name}</td>
                          <td style={{ padding: '6px 10px', color: '#555' }}>{c.car_description || '—'}</td>
                          <td style={{ padding: '6px 10px' }}>
                            <select value={c.run_group_id || ''}
                              onChange={e => handleMoveCompetitor(c, e.target.value || null)}
                              style={{ padding: '2px 6px', borderRadius: 4, border: '1px solid #ccc', fontSize: 12 }}>
                              <option value="">— unassigned —</option>
                              {runGroups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── CAMERAS ── */}
      {tab === 'cameras' && (
        <div className="card">
          <div className="card-header">Camera Management</div>
          <div style={{ padding: 16 }}>
            <p style={{ marginTop: 0, fontSize: 14, color: '#555' }}>
              Cameras appear here when they connect. Select a role and assign before starting the event.
            </p>
            {camerasWithTelemetry.length > 0 && (
              <div style={{
                marginBottom: 12,
                padding: '8px 10px',
                borderRadius: 6,
                fontSize: 13,
                background: warningCameras > 0 ? '#fff4e5' : '#ecfdf3',
                color: warningCameras > 0 ? '#92400e' : '#065f46',
                border: `1px solid ${warningCameras > 0 ? '#fcd9bd' : '#b7ebcc'}`,
              }}>
                Telemetry health: {camerasWithTelemetry.length - warningCameras} healthy, {warningCameras} needs attention.
              </div>
            )}
            {cameras.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#888', border: '2px dashed #e5e7eb', borderRadius: 8 }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>📷</div>
                <div>No cameras connected yet. Power on a RaceSpy — it will appear here within seconds.</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
                {cameras.map(cam => {
                  const cid = cam.camera_id;
                  const isOnline = cam.has_preview;
                  const telemetry = telemetryByCamera[cid];
                  const selectedRole = camRoles[cid] || cam.role as 'start' | 'finish' | null || 'start';
                  const selectedEvent = camEvents[cid] || activeEvent?.id || '';
                  const telemetryNeedsAttention = !!telemetry && (telemetry.stale || telemetry.alerts.length > 0);
                  return (
                    <div key={cid} style={{ border: `2px solid ${cam.status === 'assigned' ? '#1a56db' : isOnline ? '#e5e7eb' : '#f3f4f6'}`, borderRadius: 8, overflow: 'hidden', background: 'white' }}>
                      <div style={{ position: 'relative', background: '#111', height: 160 }}>
                        {isOnline ? (
                          <img src={`${cameraPreviewUrl(cid)}?t=${Date.now()}`} alt="preview"
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            onError={e => (e.currentTarget.style.display = 'none')} />
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666', fontSize: 13 }}>No signal</div>
                        )}
                        <div style={{ position: 'absolute', top: 6, right: 6, padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
                          background: cam.status === 'assigned' ? '#1a56db' : isOnline ? '#065f46' : '#374151', color: 'white' }}>
                          {cam.status === 'assigned' ? `✓ ${cam.role?.toUpperCase()}` : isOnline ? '● LIVE' : '○ OFFLINE'}
                        </div>
                      </div>
                      <div style={{ padding: 12 }}>
                        <div style={{ fontSize: 12, color: '#888', marginBottom: 8, fontFamily: 'monospace' }}>{cid.slice(0, 16)}…</div>
                        <div style={{
                          marginBottom: 8,
                          padding: '6px 8px',
                          borderRadius: 5,
                          background: telemetryNeedsAttention ? '#fff7ed' : '#f9fafb',
                          border: `1px solid ${telemetryNeedsAttention ? '#fed7aa' : '#e5e7eb'}`,
                          fontSize: 12,
                          color: '#374151',
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Telemetry</span>
                            <span style={{ color: telemetry?.stale ? '#b45309' : '#6b7280' }}>{formatTelemetryAge(telemetry?.telemetry_age_seconds ?? null)}</span>
                          </div>
                          {telemetry ? (
                            <div style={{ marginTop: 4, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                              <span>PPS: {telemetry.gps.pps_lock ? 'locked' : 'unlocked'}</span>
                              <span>WiFi: {telemetry.health.wifi_signal_dbm == null ? 'n/a' : `${telemetry.health.wifi_signal_dbm} dBm`}</span>
                              <span>Temp: {telemetry.health.temperature_c == null ? 'n/a' : `${telemetry.health.temperature_c.toFixed(1)} C`}</span>
                              <span>Uptime: {formatUptime(telemetry.health.uptime_seconds)}</span>
                              <span>Mem: {telemetry.health.memory_usage_percent == null ? 'n/a' : `${telemetry.health.memory_usage_percent.toFixed(0)}%`}</span>
                              <span>Disk: {telemetry.health.disk_usage_percent == null ? 'n/a' : `${telemetry.health.disk_usage_percent.toFixed(0)}%`}</span>
                              <span>Buffered: {telemetry.buffered_payloads == null ? 'n/a' : telemetry.buffered_payloads}</span>
                            </div>
                          ) : (
                            <div style={{ marginTop: 4 }}>No telemetry received yet.</div>
                          )}
                          {telemetry && telemetry.alerts.length > 0 && (
                            <div style={{ marginTop: 5, color: '#b45309' }}>
                              Alerts: {telemetry.alerts.join(', ')}
                            </div>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                          <select value={selectedRole} onChange={e => setCamRoles(r => ({ ...r, [cid]: e.target.value as any }))}
                            style={{ flex: 1, padding: '5px 8px', borderRadius: 4, border: '1px solid #ccc', fontSize: 13 }}>
                            <option value="start">🟢 Start</option>
                            <option value="finish">🏁 Finish</option>
                          </select>
                          {events.length > 1 && (
                            <select value={selectedEvent} onChange={e => setCamEvents(ev => ({ ...ev, [cid]: e.target.value }))}
                              style={{ flex: 1, padding: '5px 8px', borderRadius: 4, border: '1px solid #ccc', fontSize: 13 }}>
                              {events.map(ev => <option key={ev.id} value={ev.id}>{ev.name}</option>)}
                            </select>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button onClick={() => handleAssignCamera(cid)} disabled={assigning === cid || !selectedEvent}
                            style={btn({ flex: 1, background: '#1a56db', color: 'white' })}>
                            {assigning === cid ? 'Assigning…' : cam.status === 'assigned' ? 'Reassign' : 'Assign'}
                          </button>
                          {cam.status === 'assigned' && (
                            <button onClick={() => handleResetCamera(cid)}
                              style={btn({ background: '#fee2e2', color: '#c81e1e', fontSize: 12 })}>
                              Reset
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── RESET ── */}
      {tab === 'reset' && (
        <div className="card">
          <div className="card-header">Reset Event Data</div>
          <div style={{ padding: 16 }}>
            <p style={{ color: '#666' }}>Clears all Phase 0 runs and photos. Does not delete events or competitors.</p>
            {!confirmReset ? (
              <button style={btn({ background: '#c81e1e', color: 'white' })} onClick={() => setConfirmReset(true)}>Reset Data</button>
            ) : (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ color: '#b00020', fontWeight: 600 }}>Are you sure? Cannot be undone.</span>
                <button style={btn({ background: '#c81e1e', color: 'white' })} onClick={handleReset}>Confirm Reset</button>
                <button style={btn({ background: '#f3f4f6' })} onClick={() => setConfirmReset(false)}>Cancel</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
