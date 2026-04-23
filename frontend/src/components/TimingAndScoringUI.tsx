import { useState, useEffect } from 'react';
import {
  deleteRun, getHoldStatus, getRuns, holdStart, releaseStart, updateRun, Run,
  getAmbiguityQueue, resolveAmbiguity, listCompetitors,
  type Event, type TimingEventItem, type Competitor,
} from '../services/api';
import { formatUtcTimeWithMs } from '../utils/time';

interface TimingAndScoringUIProps {
  activeEvent: Event | null;
  onRunUpdated: (run: Run) => void;
  onError: (message: string) => void;
}

export function TimingAndScoringUI({ activeEvent, onRunUpdated, onError }: TimingAndScoringUIProps) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'active' | 'completed'>('active');
  const [isStartHeld, setIsStartHeld] = useState(false);

  // Ambiguity queue
  const [ambiguityQueue, setAmbiguityQueue] = useState<TimingEventItem[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [showAmbiguity, setShowAmbiguity] = useState(false);
  const [resolving, setResolving] = useState<string | null>(null);

  // Load all runs
  useEffect(() => {
    loadRuns();
    const interval = setInterval(loadRuns, 1500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!activeEvent) return;
    loadAmbiguityQueue();
    loadCompetitors();
    const interval = setInterval(loadAmbiguityQueue, 5000);
    return () => clearInterval(interval);
  }, [activeEvent]);

  async function loadAmbiguityQueue() {
    if (!activeEvent) return;
    try { setAmbiguityQueue(await getAmbiguityQueue(activeEvent.id)); } catch {}
  }

  async function loadCompetitors() {
    if (!activeEvent) return;
    try { setCompetitors(await listCompetitors(activeEvent.id)); } catch {}
  }

  async function handleResolve(item: TimingEventItem, action: 'select' | 'skip' | 'unknown', competitor_id?: string) {
    if (!activeEvent) return;
    setResolving(item.id);
    try {
      await resolveAmbiguity(activeEvent.id, item.id, action, competitor_id);
      await loadAmbiguityQueue();
    } catch (e) { onError(`${e}`); }
    finally { setResolving(null); }
  }

  async function loadRuns() {
    try {
      const [fetchedRuns, holdStatus] = await Promise.all([getRuns(), getHoldStatus()]);
      setRuns(fetchedRuns);
      setIsStartHeld(holdStatus.is_start_held);
    } catch (error) {
      // Ignore transient errors
    }
  }

  // Format time
  const formatTime = (seconds: number | null | undefined): string => {
    if (seconds === null || seconds === undefined) return '—';
    return seconds.toFixed(3);
  };

  // Handle penalty update
  const handlePenaltyChange = async (runId: number, delta: number) => {
    const run = runs.find(r => r.id === runId);
    if (!run) return;

    const newPenalties = Math.max(0, run.penalties + delta);
    setLoading(true);

    try {
      const updated = await updateRun(runId, { penalties: newPenalties });
      setRuns(runs.map(r => r.id === runId ? updated : r));
      onRunUpdated(updated);
    } catch (error) {
      onError(`Failed to update penalties: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle DNF toggle
  const handleDNFToggle = async (runId: number, currentDNF: boolean) => {
    setLoading(true);

    try {
      const updated = await updateRun(runId, { is_dnf: !currentDNF });
      setRuns(runs.map(r => r.id === runId ? updated : r));
      onRunUpdated(updated);
    } catch (error) {
      onError(`Failed to update DNF status: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRun = async (runId: number) => {
    setLoading(true);

    try {
      await deleteRun(runId);
      setRuns(runs.filter(r => r.id !== runId));
    } catch (error) {
      onError(`Failed to delete run: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRerunToggle = async (runId: number, currentRerun: boolean) => {
    setLoading(true);

    try {
      const updated = await updateRun(runId, {
        is_aborted: !currentRerun,
        is_missed_trip: currentRerun ? undefined : false,
      });
      setRuns(runs.map(r => r.id === runId ? updated : r));
      onRunUpdated(updated);
    } catch (error) {
      onError(`Failed to update re-run status: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Get status badge
  const getStatusBadge = (run: Run) => {
    if (run.is_aborted) {
      return <span className="badge aborted">Re-Run</span>;
    } else if (run.is_dnf) {
      return <span className="badge dnf">DNF</span>;
    } else if (run.is_missed_trip) {
      return <span className="badge aborted">Missed Trip</span>;
    } else if (run.finish_confirmed && run.finish_time) {
      return <span className="badge completed">Completed</span>;
    } else {
      return <span className="badge active">Active</span>;
    }
  };

  const isActiveRun = (run: Run) => !run.finish_confirmed && !run.is_dnf && !run.is_aborted;
  const isCompletedRun = (run: Run) => !isActiveRun(run);
  const missedTripRun = runs.find(run => isActiveRun(run) && run.is_missed_trip);

  const filteredRuns = runs.filter(run => {
    if (activeFilter === 'active') return isActiveRun(run);
    return isCompletedRun(run);
  });

  const handleToggleStartHold = async () => {
    setLoading(true);
    try {
      if (isStartHeld) {
        const result = await releaseStart();
        setIsStartHeld(result.is_start_held);
      } else {
        const result = await holdStart();
        setIsStartHeld(result.is_start_held);
      }
      await loadRuns();
    } catch (error) {
      onError(`Failed to update start hold: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>

      {/* Ambiguity Queue Banner */}
      {activeEvent && ambiguityQueue.length > 0 && (
        <div style={{ marginBottom: 12, padding: '10px 16px', background: '#fef3c7', border: '1px solid #d97706', borderRadius: 8, cursor: 'pointer' }}
          onClick={() => setShowAmbiguity(v => !v)}>
          <strong>⚠️ {ambiguityQueue.length} timing event{ambiguityQueue.length !== 1 ? 's' : ''} need identification</strong>
          <span style={{ marginLeft: 8, fontSize: 13, color: '#92400e' }}>{showAmbiguity ? '▲ Hide' : '▼ Review'}</span>
        </div>
      )}

      {/* Ambiguity Queue Panel */}
      {showAmbiguity && activeEvent && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="card-header">Ambiguity Queue</div>
          <div style={{ padding: 12 }}>
            {ambiguityQueue.map(item => {
              return (
                <div key={item.id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, marginBottom: 12, overflow: 'hidden' }}>
                  <div style={{ display: 'flex', gap: 12, padding: 12 }}>
                    {item.image_path && (
                      <img src={`/api/v1/events/${activeEvent.id}/timing-events/${item.id}/image`}
                        alt="trigger" style={{ width: 120, height: 80, objectFit: 'cover', borderRadius: 4 }}
                        onError={e => (e.currentTarget.style.display = 'none')} />
                    )}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, color: '#555', marginBottom: 6 }}>
                        <strong>{item.role.toUpperCase()}</strong> — {new Date(item.timestamp_utc_ms).toLocaleTimeString()}
                        {item.ocr_detail?.raw_text && <span style={{ marginLeft: 8 }}>OCR: "{item.ocr_detail.raw_text}"</span>}
                      </div>
                      {item.suggested_competitor && (
                        <div style={{ fontSize: 13, padding: '4px 8px', background: '#eff6ff', borderRadius: 4, marginBottom: 6, display: 'inline-block' }}>
                          Suggested: <strong>#{item.suggested_competitor.number} {item.suggested_competitor.class_code}</strong> — {item.suggested_competitor.driver_name}
                        </div>
                      )}
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                        {item.suggested_competitor && (
                          <button disabled={resolving === item.id}
                            onClick={() => handleResolve(item, 'select', item.suggested_competitor!.id)}
                            style={{ padding: '4px 12px', background: '#1a56db', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
                            ✓ Confirm #{item.suggested_competitor.number}
                          </button>
                        )}
                        <select onChange={e => { if (e.target.value) handleResolve(item, 'select', e.target.value); }}
                          style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #ccc', fontSize: 13 }}>
                          <option value="">Select competitor…</option>
                          {competitors.map(c => <option key={c.id} value={c.id}>#{c.number} {c.class_code} — {c.driver_name}</option>)}
                        </select>
                        <button disabled={resolving === item.id} onClick={() => handleResolve(item, 'skip')}
                          style={{ padding: '4px 10px', background: '#f3f4f6', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
                          Skip
                        </button>
                        <button disabled={resolving === item.id} onClick={() => handleResolve(item, 'unknown')}
                          style={{ padding: '4px 10px', background: '#fee2e2', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}>
                          Unknown
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">Timing & Scoring UI</div>

        <div style={{ marginBottom: '12px' }}>
          <button
            className={isStartHeld ? 'success' : 'warning'}
            onClick={handleToggleStartHold}
            disabled={loading}
          >
            {isStartHeld ? 'Release Start' : 'Hold Start'}
          </button>
        </div>

        {isStartHeld && (
          <div className="alert-banner hold" style={{ marginBottom: '12px' }}>
            <div className="timing-hold-banner">
              <span>
                {missedTripRun
                  ? `⚠️ HOLD STARTS - Missed trip detected for Car #${missedTripRun.car?.number || missedTripRun.car_id}. Wait for recovery or release start.`
                  : '⚠️ HOLD STARTS - Timing has starts paused. Release start when ready.'}
              </span>
            </div>
          </div>
        )}

        <div className="sub-tabs" style={{ marginBottom: '12px' }}>
          <button className={activeFilter === 'active' ? 'active' : ''} onClick={() => setActiveFilter('active')}>Active Runs</button>
          <button className={activeFilter === 'completed' ? 'active' : ''} onClick={() => setActiveFilter('completed')}>Completed Runs</button>
        </div>

        {filteredRuns.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
            No runs for this filter
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th style={{ width: '80px' }}>Photo</th>
                  <th style={{ width: '70px' }}>Run #</th>
                  <th style={{ width: '60px' }}>Car #</th>
                  <th style={{ width: '70px' }}>Class</th>
                  <th style={{ width: '120px' }}>Start Time</th>
                  <th style={{ width: '120px' }}>Finish Time</th>
                  <th style={{ width: '80px' }}>Raw Time (s)</th>
                  <th style={{ width: '60px' }}>Penalties</th>
                  <th style={{ width: '80px' }}>Adjusted (s)</th>
                  <th style={{ width: '100px' }}>Status</th>
                  <th style={{ width: '200px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRuns.map(run => (
                  <tr key={run.id} className={run.is_missed_trip ? 'timing-row-hold' : ''}>
                    {/* Photo */}
                    <td>
                      {run.start_photo_url ? (
                        <img
                          src={run.start_photo_url}
                          alt="Start"
                          style={{
                            maxWidth: '100%',
                            height: 'auto',
                            borderRadius: '4px',
                            maxHeight: '60px'
                          }}
                        />
                      ) : (
                        <span style={{ color: '#999' }}>—</span>
                      )}
                    </td>

                    {/* Run number */}
                    <td>
                      <strong>{run.id}</strong>
                    </td>

                    {/* Car number */}
                    <td>
                      <strong>{run.car?.number}</strong>
                    </td>

                    {/* Class */}
                    <td>{run.car?.class_name}</td>

                    {/* Start time */}
                    <td style={{ fontSize: '12px', fontFamily: 'monospace' }}>
                      {formatUtcTimeWithMs(run.start_time)}
                    </td>

                    {/* Finish time */}
                    <td style={{ fontSize: '12px', fontFamily: 'monospace' }}>
                      {run.finish_time ? formatUtcTimeWithMs(run.finish_time) : '—'}
                    </td>

                    {/* Raw time */}
                    <td style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                      {formatTime(run.raw_time)}
                    </td>

                    {/* Penalties */}
                    <td style={{ textAlign: 'center' }}>
                      <strong>{run.penalties}</strong>
                    </td>

                    {/* Adjusted time */}
                    <td style={{ fontFamily: 'monospace', fontWeight: 'bold', color: '#007bff' }}>
                      {formatTime(run.adjusted_time)}
                    </td>

                    {/* Status */}
                    <td>{getStatusBadge(run)}</td>

                    {/* Actions */}
                    <td>
                      <div className="timing-controls">
                        <button
                          className="primary"
                          onClick={() => handlePenaltyChange(run.id, 1)}
                          disabled={loading}
                          title="Add 1 penalty unit"
                        >
                          +1
                        </button>
                        <button
                          className="primary"
                          onClick={() => handlePenaltyChange(run.id, 2)}
                          disabled={loading}
                          title="Add 2 penalty units"
                        >
                          +2
                        </button>
                        <button
                          className="secondary"
                          onClick={() => handlePenaltyChange(run.id, -run.penalties)}
                          disabled={loading || run.penalties === 0}
                          title="Clear penalties"
                        >
                          ✕
                        </button>
                      </div>

                      <div className="timing-controls" style={{ marginTop: '6px' }}>
                        <button
                          className={run.is_dnf ? 'danger' : 'warning'}
                          onClick={() => handleDNFToggle(run.id, run.is_dnf)}
                          disabled={loading}
                          title={run.is_dnf ? 'Unmark DNF' : 'Mark DNF'}
                          style={{ fontSize: '12px', padding: '4px 8px' }}
                        >
                          {run.is_dnf ? '✓ DNF' : 'DNF'}
                        </button>
                        <button
                          className="danger"
                          onClick={() => handleDeleteRun(run.id)}
                          disabled={loading}
                          title="Delete this run"
                          style={{ fontSize: '12px', padding: '4px 8px' }}
                        >
                          Delete
                        </button>
                        <button
                          className={run.is_aborted ? 'danger' : 'warning'}
                          onClick={() => handleRerunToggle(run.id, run.is_aborted)}
                          disabled={loading}
                          title={run.is_aborted ? 'Unmark Re-Run' : 'Mark Re-Run'}
                          style={{ fontSize: '12px', padding: '4px 8px' }}
                        >
                          {run.is_aborted ? '✓ Re-Run' : 'Re-Run'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
