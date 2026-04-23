import { useState, useEffect } from 'react';
import { getRuns, finishRun, holdStart, updateRun, Run } from '../services/api';
import { parseApiUtcDate } from '../utils/time';

interface FinishWorkerUIProps {
  finishTriggered: boolean;
  finishTriggeredAt: string | null;
  onRunFinished: (run: Run) => void;
  onError: (message: string) => void;
  onTriggerFinish?: () => Promise<void>;
}

export function FinishWorkerUI({ finishTriggered, finishTriggeredAt, onRunFinished, onError, onTriggerFinish: _onTriggerFinish }: FinishWorkerUIProps) {
  const [activeRuns, setActiveRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  // Load active runs
  useEffect(() => {
    loadActiveRuns();
    const interval = setInterval(loadActiveRuns, 2000); // Refresh every 2 seconds
    return () => clearInterval(interval);
  }, []);

  async function loadActiveRuns() {
    try {
      const runs = await getRuns('active');
      setActiveRuns(runs);
    } catch (error) {
      onError(`Failed to load runs: ${error}`);
    }
  }

  // Reset selected run when trigger window expires.
  useEffect(() => {
    if (!finishTriggered) {
      setSelectedRunId(null);
    }
  }, [finishTriggered]);

  // Select finish photo
  const selectFinishPhoto = (runId: number) => {
    setSelectedRunId(runId);
  };

  // Confirm finish
  const handleConfirmFinish = async () => {
    if (selectedRunId === null) {
      onError('Please select a car');
      return;
    }

    setLoading(true);
    try {
      // Create a simple finish photo (1x1 pixel as placeholder)
      const canvas = document.createElement('canvas');
      canvas.width = 1;
      canvas.height = 1;
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.fillStyle = '#000';
      else {
        throw new Error('Could not get canvas context');
      }
      ctx.fill();

      let finishPhoto: File;
      await new Promise<void>(resolve => {
        canvas.toBlob(blob => {
          if (blob) {
            finishPhoto = new File([blob], `finish_${Date.now()}.jpg`, { type: 'image/jpeg' });
          }
          resolve();
        }, 'image/jpeg');
      });

      if (!finishPhoto!) {
        throw new Error('Failed to create finish photo');
      }

      const finishedRun = await finishRun(selectedRunId, finishPhoto);
      onRunFinished(finishedRun);

      // Reset state
      setSelectedRunId(null);
      await loadActiveRuns();
    } catch (error) {
      onError(`Failed to finish run: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkMissedTrip = async (runId: number) => {
    setLoading(true);
    try {
      await updateRun(runId, { is_missed_trip: true });
      await holdStart();
      if (selectedRunId === runId) {
        setSelectedRunId(null);
      }
      await loadActiveRuns();
    } catch (error) {
      onError(`Failed to flag missed trip: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const oldestActiveRun = activeRuns.reduce<Run | null>((oldest, run) => {
    if (!oldest) return run;
    return parseApiUtcDate(run.start_time).getTime() < parseApiUtcDate(oldest.start_time).getTime() ? run : oldest;
  }, null);

  const triggerTimestampMs = finishTriggeredAt ? parseApiUtcDate(finishTriggeredAt).getTime() : null;

  const expectedElapsedSeconds = oldestActiveRun && triggerTimestampMs !== null
    ? Math.max(0, (triggerTimestampMs - parseApiUtcDate(oldestActiveRun.start_time).getTime()) / 1000)
    : null;

  // Auto-select the oldest active run when a finish trigger is detected.
  useEffect(() => {
    if (!finishTriggered) return;
    if (selectedRunId !== null) return;
    if (oldestActiveRun) {
      setSelectedRunId(oldestActiveRun.id);
    }
  }, [finishTriggered, oldestActiveRun, selectedRunId]);

  // Clear stale selection if the selected run leaves the active list.
  useEffect(() => {
    if (selectedRunId === null) return;
    const stillActive = activeRuns.some(run => run.id === selectedRunId);
    if (!stillActive) {
      setSelectedRunId(null);
    }
  }, [activeRuns, selectedRunId]);

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div className="card">
        <div className="card-header">Finish Worker UI</div>

        {finishTriggered && (
          <div className="finish-trigger-panel">
            <div className="finish-trigger-banner">
              Car crossing finish line! Select the matching photo below.
            </div>
            {oldestActiveRun && expectedElapsedSeconds !== null && (
              <div className="finish-expected-time">
                Expected next: Car #{oldestActiveRun.car?.number || oldestActiveRun.car_id} at {expectedElapsedSeconds.toFixed(3)}s (at trigger)
              </div>
            )}
          </div>
        )}

        {/* Active runs photo grid */}
        {activeRuns.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>
            No active runs waiting for finish
          </div>
        ) : (
          <div>
            <strong>Select car that crossed finish:</strong>
            <div className="photo-grid">
              {activeRuns.map(run => (
                <div
                  key={run.id}
                  className={`photo-thumbnail ${selectedRunId === run.id ? 'selected' : ''} ${run.is_missed_trip ? 'missed-trip' : ''}`}
                  style={{ opacity: finishTriggered ? 1 : 0.6 }}
                >
                  <div
                    onClick={() => selectFinishPhoto(run.id)}
                    style={{
                      width: '100%',
                      height: '100%',
                      pointerEvents: finishTriggered ? 'auto' : 'none'
                    }}
                  >
                  {run.start_photo_url ? (
                    <img src={run.start_photo_url} alt={`Car ${run.car?.number}`} />
                  ) : (
                    <div style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: '#f5f5f5',
                      color: '#999'
                    }}>
                      No photo
                    </div>
                  )}
                  </div>
                  <div className="photo-label">
                    #{run.car?.number} - {run.car?.class_name}
                  </div>
                  <button
                    className="danger"
                    onClick={() => handleMarkMissedTrip(run.id)}
                    disabled={loading}
                    style={{
                      position: 'absolute',
                      top: '8px',
                      right: '8px',
                      padding: '4px 8px',
                      fontSize: '11px',
                      zIndex: 2
                    }}
                    title="Flag missed trip for this car"
                  >
                    🚫 Missed Trip
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Confirm finish button */}
        <button
          className="success"
          onClick={handleConfirmFinish}
          disabled={!finishTriggered || selectedRunId === null || loading}
          style={{ width: '100%', marginTop: '20px' }}
        >
          {loading ? <span className="spinner"></span> : '✓ Confirm Finish'}
        </button>
      </div>
    </div>
  );
}
