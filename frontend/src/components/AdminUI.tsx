import { useState, useEffect, useRef } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  listEvents, createEvent, updateEvent,
  listRunGroups, createRunGroup, deleteRunGroup,
  getAssignmentSummary, bulkAssign,
  listCompetitors, updateCompetitor, importCompetitorsCSV,
  listCameras, resetData,
  type Event, type RunGroup, type Competitor, type ClassSummary, type Camera,
} from '../services/api';

interface AdminUIProps {
  activeEvent: Event | null;
  onEventChange: (event: Event | null) => void;
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}

type AdminTab = 'event' | 'groups' | 'competitors' | 'cameras' | 'reset';

export function AdminUI({ activeEvent, onEventChange, onError, onSuccess }: AdminUIProps) {
  const [tab, setTab] = useState<AdminTab>('event');
  const [events, setEvents] = useState<Event[]>([]);
  const [runGroups, setRunGroups] = useState<RunGroup[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [classSummary, setClassSummary] = useState<ClassSummary[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);

  // Event creation
  const [newEventName, setNewEventName] = useState('');
  const [newEventDate, setNewEventDate] = useState('');
  const [newEventMode, setNewEventMode] = useState<'human' | 'racespy'>('human');
  const [creatingEvent, setCreatingEvent] = useState(false);

  // Run group creation
  const [newGroupName, setNewGroupName] = useState('');

  // Bulk assignment: class_code → run_group_id
  const [bulkMap, setBulkMap] = useState<Record<string, string>>({});

  // Camera QR
  const [qrRole, setQrRole] = useState<'start' | 'finish'>('start');

  // CSV import
  const csvRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  // Confirm reset
  const [confirmReset, setConfirmReset] = useState(false);

  useEffect(() => { loadEvents(); }, []);
  useEffect(() => {
    if (!activeEvent) return;
    if (tab === 'groups' || tab === 'competitors') loadGroupsAndSummary();
    if (tab === 'competitors') loadCompetitors();
    if (tab === 'cameras') loadCameras();
  }, [activeEvent, tab]);

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
      const init: Record<string, string> = {};
      summary.forEach(c => { if (c.assigned_group_id) init[c.class_code] = c.assigned_group_id; });
      setBulkMap(init);
    } catch (e) { onError(`${e}`); }
  }

  async function loadCompetitors() {
    if (!activeEvent) return;
    try { setCompetitors(await listCompetitors(activeEvent.id)); } catch (e) { onError(`${e}`); }
  }

  async function loadCameras() {
    try { setCameras(await listCameras()); } catch (e) { onError(`${e}`); }
  }

  async function handleCreateEvent() {
    if (!newEventName.trim()) return;
    setCreatingEvent(true);
    try {
      const ev = await createEvent(newEventName.trim(), newEventDate || null, newEventMode);
      onSuccess(`Event "${ev.name}" created`);
      setNewEventName('');
      setNewEventDate('');
      await loadEvents();
      onEventChange(ev);
    } catch (e) { onError(`${e}`); }
    finally { setCreatingEvent(false); }
  }

  async function handleSelectEvent(ev: Event) {
    onEventChange(ev);
    setTab('groups');
  }

  async function handleUpdateMode(mode: 'human' | 'racespy') {
    if (!activeEvent) return;
    try {
      const updated = await updateEvent(activeEvent.id, { timing_mode: mode });
      onEventChange(updated);
      onSuccess(`Timing mode set to ${mode}`);
    } catch (e) { onError(`${e}`); }
  }

  async function handleCreateGroup() {
    if (!activeEvent || !newGroupName.trim()) return;
    try {
      await createRunGroup(activeEvent.id, newGroupName.trim(), runGroups.length);
      setNewGroupName('');
      onSuccess('Run group created');
      await loadGroupsAndSummary();
    } catch (e) { onError(`${e}`); }
  }

  async function handleDeleteGroup(id: string) {
    if (!activeEvent) return;
    try {
      await deleteRunGroup(activeEvent.id, id);
      onSuccess('Run group deleted');
      await loadGroupsAndSummary();
    } catch (e) { onError(`${e}`); }
  }

  async function handleBulkAssign() {
    if (!activeEvent) return;
    const assignments = Object.entries(bulkMap)
      .filter(([, gid]) => !!gid)
      .map(([class_code, run_group_id]) => ({ class_code, run_group_id }));
    if (!assignments.length) { onError('No classes mapped to groups'); return; }
    try {
      const r = await bulkAssign(activeEvent.id, assignments);
      onSuccess(`${r.competitors_updated} competitors assigned`);
      await loadGroupsAndSummary();
    } catch (e) { onError(`${e}`); }
  }

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

  async function handleReset() {
    try {
      const r = await resetData();
      onSuccess(`Reset: ${r.runs_deleted} runs deleted`);
      setConfirmReset(false);
    } catch (e) { onError(`${e}`); }
  }

  const qrPayload = activeEvent
    ? JSON.stringify({ role: qrRole, event_id: activeEvent.id })
    : '';

  const btnStyle: React.CSSProperties = { padding: '6px 14px', cursor: 'pointer', borderRadius: 4, border: '1px solid #ccc' };
  const primaryBtn: React.CSSProperties = { ...btnStyle, background: '#1a56db', color: 'white', border: 'none' };
  const dangerBtn: React.CSSProperties = { ...btnStyle, background: '#c81e1e', color: 'white', border: 'none' };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Sub-navigation */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {(['event', 'groups', 'competitors', 'cameras', 'reset'] as AdminTab[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ ...btnStyle, background: tab === t ? '#1a56db' : '#f3f4f6', color: tab === t ? 'white' : '#333', border: 'none' }}>
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
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
              <input placeholder="Event name" value={newEventName} onChange={e => setNewEventName(e.target.value)}
                style={{ flex: 1, minWidth: 200, padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc' }} />
              <input type="date" value={newEventDate} onChange={e => setNewEventDate(e.target.value)}
                style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc' }} />
              <select value={newEventMode} onChange={e => setNewEventMode(e.target.value as any)}
                style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc' }}>
                <option value="human">Human timing</option>
                <option value="racespy">RaceSpy + Staging</option>
              </select>
              <button style={primaryBtn} onClick={handleCreateEvent} disabled={creatingEvent}>
                {creatingEvent ? 'Creating…' : 'Create Event'}
              </button>
            </div>

            <h3>Existing Events</h3>
            {events.length === 0 && <p style={{ color: '#888' }}>No events yet.</p>}
            {events.map(ev => (
              <div key={ev.id} onClick={() => handleSelectEvent(ev)}
                style={{ padding: 12, border: `2px solid ${activeEvent?.id === ev.id ? '#1a56db' : '#e5e7eb'}`,
                  borderRadius: 6, marginBottom: 8, cursor: 'pointer', background: activeEvent?.id === ev.id ? '#eff6ff' : 'white' }}>
                <strong>{ev.name}</strong>
                <span style={{ marginLeft: 12, color: '#555', fontSize: 13 }}>{ev.date || 'No date'}</span>
                <span style={{ marginLeft: 8, fontSize: 12, padding: '2px 8px', borderRadius: 12,
                  background: ev.status === 'active' ? '#def7ec' : '#f3f4f6', color: ev.status === 'active' ? '#03543f' : '#555' }}>
                  {ev.status}
                </span>
                <span style={{ marginLeft: 8, fontSize: 12, padding: '2px 8px', borderRadius: 12, background: '#fef3c7', color: '#92400e' }}>
                  {ev.timing_mode}
                </span>
              </div>
            ))}

            {activeEvent && (
              <div style={{ marginTop: 16, padding: 12, background: '#f9fafb', borderRadius: 6 }}>
                <strong>Active: {activeEvent.name}</strong>
                <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                  <span style={{ alignSelf: 'center', fontSize: 13 }}>Timing mode:</span>
                  <button style={{ ...btnStyle, background: activeEvent.timing_mode === 'human' ? '#1a56db' : '#f3f4f6', color: activeEvent.timing_mode === 'human' ? 'white' : '#333', border: 'none' }}
                    onClick={() => handleUpdateMode('human')}>Human</button>
                  <button style={{ ...btnStyle, background: activeEvent.timing_mode === 'racespy' ? '#1a56db' : '#f3f4f6', color: activeEvent.timing_mode === 'racespy' ? 'white' : '#333', border: 'none' }}
                    onClick={() => handleUpdateMode('racespy')}>RaceSpy + Staging</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── RUN GROUPS ── */}
      {tab === 'groups' && (
        <div className="card">
          <div className="card-header">Run Groups {activeEvent ? `— ${activeEvent.name}` : '(no event selected)'}</div>
          {!activeEvent ? <p style={{ padding: 16, color: '#888' }}>Select an event first.</p> : (
            <div style={{ padding: 16 }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                <input placeholder="Group name (e.g. Group 1)" value={newGroupName}
                  onChange={e => setNewGroupName(e.target.value)}
                  style={{ flex: 1, padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc' }} />
                <button style={primaryBtn} onClick={handleCreateGroup}>Add Group</button>
              </div>

              {runGroups.map(g => (
                <div key={g.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: 6, marginBottom: 6 }}>
                  <span><strong>{g.name}</strong> <span style={{ color: '#888', fontSize: 13 }}>({g.competitor_count} competitors)</span></span>
                  <button style={{ ...dangerBtn, padding: '4px 10px', fontSize: 12 }} onClick={() => handleDeleteGroup(g.id)}>Delete</button>
                </div>
              ))}

              {runGroups.length > 0 && classSummary.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <h3 style={{ marginBottom: 8 }}>Bulk Assign by Class</h3>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                    <thead>
                      <tr style={{ background: '#f3f4f6' }}>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Class</th>
                        <th style={{ padding: '6px 10px', textAlign: 'right' }}>Competitors</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Assign to Group</th>
                      </tr>
                    </thead>
                    <tbody>
                      {classSummary.map(c => (
                        <tr key={c.class_code} style={{ borderTop: '1px solid #e5e7eb' }}>
                          <td style={{ padding: '6px 10px' }}>
                            <strong>{c.class_code}</strong>
                            {c.split && <span style={{ marginLeft: 6, color: '#d97706', fontSize: 12 }}>⚠ split</span>}
                          </td>
                          <td style={{ padding: '6px 10px', textAlign: 'right' }}>{c.competitor_count}</td>
                          <td style={{ padding: '6px 10px' }}>
                            <select value={bulkMap[c.class_code] || ''}
                              onChange={e => setBulkMap(m => ({ ...m, [c.class_code]: e.target.value }))}
                              style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #ccc' }}>
                              <option value="">— unassigned —</option>
                              {runGroups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <button style={{ ...primaryBtn, marginTop: 12 }} onClick={handleBulkAssign}>Apply Assignments</button>
                </div>
              )}
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
                <label style={{ ...primaryBtn, cursor: 'pointer' }}>
                  {importing ? 'Importing…' : '📁 Import CSV (MotorsportsReg)'}
                  <input ref={csvRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleCSVImport} disabled={importing} />
                </label>
                <span style={{ color: '#888', fontSize: 13 }}>{competitors.length} competitors loaded</span>
              </div>

              {competitors.length === 0 ? (
                <p style={{ color: '#888' }}>No competitors imported yet. Upload a MotorsportsReg CSV export.</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#f3f4f6' }}>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>#</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Class</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Driver</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Car</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left' }}>Group</th>
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
          <div className="card-header">Cameras & QR Codes</div>
          <div style={{ padding: 16 }}>
            {!activeEvent ? (
              <p style={{ color: '#888' }}>Select an event first to generate QR codes.</p>
            ) : (
              <>
                <p style={{ marginTop: 0, fontSize: 14, color: '#555' }}>
                  Point each RaceSpy's camera at the QR code for its role. The camera will register itself and enter Armed mode.
                </p>
                <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
                  {(['start', 'finish'] as const).map(r => (
                    <button key={r} onClick={() => setQrRole(r)}
                      style={{ ...btnStyle, background: qrRole === r ? '#1a56db' : '#f3f4f6', color: qrRole === r ? 'white' : '#333', border: 'none' }}>
                      {r === 'start' ? '🟢 Start' : '🏁 Finish'}
                    </button>
                  ))}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: 24, background: 'white', border: '2px solid #e5e7eb', borderRadius: 8 }}>
                  <QRCodeSVG value={qrPayload} size={220} />
                  <div style={{ fontWeight: 600, fontSize: 18 }}>{qrRole.toUpperCase()} LINE</div>
                  <div style={{ fontSize: 12, color: '#888', wordBreak: 'break-all', maxWidth: 300, textAlign: 'center' }}>{qrPayload}</div>
                </div>
              </>
            )}

            <h3 style={{ marginTop: 24 }}>Registered Cameras</h3>
            {cameras.length === 0 ? (
              <p style={{ color: '#888' }}>No cameras registered yet.</p>
            ) : (
              cameras.map(cam => (
                <div key={cam.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px',
                  border: '1px solid #e5e7eb', borderRadius: 6, marginBottom: 6, fontSize: 13 }}>
                  <span>{cam.role?.toUpperCase() || 'UNASSIGNED'} — <code style={{ fontSize: 11 }}>{cam.id.slice(0, 8)}</code></span>
                  <span style={{ padding: '2px 8px', borderRadius: 12,
                    background: cam.status === 'active' ? '#def7ec' : cam.status === 'registered' ? '#fef3c7' : '#f3f4f6',
                    color: cam.status === 'active' ? '#03543f' : cam.status === 'registered' ? '#92400e' : '#555' }}>
                    {cam.status}
                  </span>
                </div>
              ))
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
              <button style={dangerBtn} onClick={() => setConfirmReset(true)}>Reset Data</button>
            ) : (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ color: '#b00020', fontWeight: 600 }}>Are you sure? Cannot be undone.</span>
                <button style={dangerBtn} onClick={handleReset}>Confirm Reset</button>
                <button style={btnStyle} onClick={() => setConfirmReset(false)}>Cancel</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
