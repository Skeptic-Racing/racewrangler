import { useEffect, useRef, useState } from 'react';
import { StarterUI } from './components/StarterUI';
import { FinishWorkerUI } from './components/FinishWorkerUI';
import { TimingAndScoringUI } from './components/TimingAndScoringUI';
import { AdminUI } from './components/AdminUI';
import { getFinishTriggerStatus, Run, triggerFinish } from './services/api';
import './styles/main.css';

type TabType = 'starter' | 'finish' | 'timing' | 'admin';

interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('starter');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [finishTriggered, setFinishTriggered] = useState(false);
  const [finishTriggeredAt, setFinishTriggeredAt] = useState<string | null>(null);
  const toastIdRef = useRef(0);

  useEffect(() => {
    let mounted = true;

    const syncFinishTrigger = async () => {
      try {
        const status = await getFinishTriggerStatus();
        if (mounted) {
          setFinishTriggered(status.is_finish_triggered);
          setFinishTriggeredAt(status.is_finish_triggered ? status.finish_triggered_at : null);
        }
      } catch {
        // Ignore transient polling failures to avoid noisy toasts.
      }
    };

    syncFinishTrigger();
    const interval = setInterval(syncFinishTrigger, 500);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Show toast notification
  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = toastIdRef.current++;
    setToasts(prev => [...prev, { id, message, type }]);

    // Auto-remove toast after 5 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  // Handlers
  const handleRunStarted = (run: Run) => {
    showToast(`✓ Run #${run.id} started for car #${run.car?.number}`, 'success');
  };

  const handleRunFinished = (run: Run) => {
    showToast(
      `✓ Run #${run.id} finished (${run.raw_time?.toFixed(3)}s)`,
      'success'
    );
  };

  const handleRunUpdated = (run: Run) => {
    showToast(`✓ Run #${run.id} updated`, 'success');
  };

  const handleError = (message: string) => {
    showToast(message, 'error');
  };

  const handleTriggerFinish = async () => {
    try {
      const status = await triggerFinish();
      setFinishTriggered(status.is_finish_triggered);
      setFinishTriggeredAt(status.finish_triggered_at);
    } catch (error) {
      handleError(`Failed to trigger finish: ${error}`);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      {/* Header */}
      <header style={{
        backgroundColor: '#333',
        color: 'white',
        padding: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <div className="container">
          <h1 style={{ margin: 0, fontSize: '28px' }}>🏁 Race Wrangler POC</h1>
          <p style={{ margin: '8px 0 0 0', color: '#aaa', fontSize: '14px' }}>
            Motorsports Timing & Scoring System
          </p>
        </div>
      </header>

      {/* Navigation tabs */}
      <div className="container" style={{ paddingTop: '20px' }}>
        <nav className="nav-tabs">
          <button
            className={activeTab === 'starter' ? 'active' : ''}
            onClick={() => setActiveTab('starter')}
          >
            👤 Starter UI
          </button>
          <button
            className={activeTab === 'finish' ? 'active' : ''}
            onClick={() => setActiveTab('finish')}
          >
            🏁 Finish Worker UI
          </button>
          <button
            className={activeTab === 'timing' ? 'active' : ''}
            onClick={() => setActiveTab('timing')}
          >
            ⏱️ Timing & Scoring
          </button>
          <button
            className={activeTab === 'admin' ? 'active' : ''}
            onClick={() => setActiveTab('admin')}
          >
            ⚙️ Admin
          </button>
        </nav>
      </div>

      {/* Main content */}
      <main className="container" style={{ minHeight: 'calc(100vh - 180px)' }}>
        {activeTab === 'starter' && (
          <StarterUI onRunStarted={handleRunStarted} onError={handleError} />
        )}

        {activeTab === 'finish' && (
          <FinishWorkerUI
            finishTriggered={finishTriggered}
            finishTriggeredAt={finishTriggeredAt}
            onRunFinished={handleRunFinished}
            onError={handleError}
          />
        )}

        {activeTab === 'timing' && (
          <TimingAndScoringUI onRunUpdated={handleRunUpdated} onError={handleError} />
        )}

        {activeTab === 'admin' && (
          <AdminUI
            finishTriggered={finishTriggered}
            onTriggerFinish={handleTriggerFinish}
            onResetDone={(message) => showToast(message, 'success')}
            onError={handleError}
          />
        )}
      </main>

      {/* Toast notifications */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast ${toast.type}`}>
            {toast.message}
          </div>
        ))}
      </div>

      {/* Footer */}
      <footer style={{
        backgroundColor: '#f9f9f9',
        borderTop: '1px solid #ddd',
        padding: '20px',
        textAlign: 'center',
        color: '#666',
        fontSize: '12px'
      }}>
        <div className="container">
          <p>Race Wrangler POC v0.1.0 | Local-First Timing & Scoring</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
