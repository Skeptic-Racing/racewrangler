import { useState } from 'react';
import { resetData } from '../services/api';

interface AdminUIProps {
  finishTriggered: boolean;
  onTriggerFinish: () => Promise<void>;
  onResetDone: (message: string) => void;
  onError: (message: string) => void;
}

export function AdminUI({ finishTriggered, onTriggerFinish, onResetDone, onError }: AdminUIProps) {
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [triggerLoading, setTriggerLoading] = useState(false);

  const handleResetData = async () => {
    setResetLoading(true);
    try {
      const result = await resetData();
      onResetDone(`✓ Reset complete: ${result.runs_deleted} runs deleted, ${result.photos_deleted} photos deleted`);
      setConfirmReset(false);
    } catch (error) {
      onError(`Failed to reset data: ${error}`);
    } finally {
      setResetLoading(false);
    }
  };

  const handleTriggerFinish = async () => {
    setTriggerLoading(true);
    try {
      await onTriggerFinish();
    } finally {
      setTriggerLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div className="card">
        <div className="card-header">Admin UI</div>

        <div className="admin-section">
          <h3 style={{ marginBottom: '10px' }}>Finish Trigger</h3>
          <button
            className="warning"
            onClick={handleTriggerFinish}
            disabled={triggerLoading}
            style={{ width: '100%', marginBottom: '12px' }}
          >
            {triggerLoading
              ? 'Sending Trigger...'
              : (finishTriggered ? '🔴 FINISH TRIGGER DETECTED!' : '⏱️ Simulate Finish Trigger')}
          </button>

          {finishTriggered && (
            <div className="admin-alert warning">
              Car crossing finish line! Finish worker can select the matching car now.
            </div>
          )}
        </div>

        <div className="admin-section" style={{ marginTop: '24px' }}>
          <h3 style={{ marginBottom: '10px' }}>Reset Event Data</h3>
          <p style={{ color: '#666', marginBottom: '12px' }}>
            This clears all runs and photos and resets run numbers.
          </p>

          {!confirmReset ? (
            <button className="danger" onClick={() => setConfirmReset(true)}>
              Reset Data
            </button>
          ) : (
            <div className="admin-confirm-row">
              <span style={{ color: '#b00020', fontWeight: 600 }}>
                Are you sure? This cannot be undone.
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="secondary"
                  onClick={() => setConfirmReset(false)}
                  disabled={resetLoading}
                >
                  Cancel
                </button>
                <button className="danger" onClick={handleResetData} disabled={resetLoading}>
                  {resetLoading ? <span className="spinner"></span> : 'Confirm Reset'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
