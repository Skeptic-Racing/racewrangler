import { useEffect, useRef, useState } from 'react';
import { StarterUI } from './components/StarterUI';
import { FinishWorkerUI } from './components/FinishWorkerUI';
import { TimingAndScoringUI } from './components/TimingAndScoringUI';
import { AdminUI } from './components/AdminUI';
import { StagingUI } from './components/StagingUI';
import { getFinishTriggerStatus, Run, triggerFinish, type Event } from './services/api';
import './styles/main.css';

type TabType = 'starter' | 'finish' | 'staging' | 'timing' | 'admin';

interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
}

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('admin');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [finishTriggered, setFinishTriggered] = useState(false);
  const [finishTriggeredAt, setFinishTriggeredAt] = useState<string | null>(null);
  const [activeEvent, setActiveEvent] = useState<Event | null>(null);
  const toastIdRef = useRef(0);

  useEffect(() => {
    // Connect to WebSocket for real-time updates (replaces 500ms polling)
    const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
    let ws: WebSocket | null = null;
    let pingInterval: ReturnType<typeof setInterval>;
    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let mounted = true;

    function connect() {
      if (!mounted) return;
      ws = new WebSocket(wsUrl);

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'finish_trigger') {
            setFinishTriggered(msg.data.is_finish_triggered);
            setFinishTriggeredAt(msg.data.is_finish_triggered ? msg.data.finish_triggered_at : null);
          }
        } catch {}
      };

      ws.onopen = () => {
        // Keep-alive ping every 30s
        pingInterval = setInterval(() => ws?.readyState === WebSocket.OPEN && ws.send('ping'), 30000);
        // Fetch current state once on connect in case we missed events while disconnected
        getFinishTriggerStatus().then(s => {
          if (!mounted) return;
          setFinishTriggered(s.is_finish_triggered);
          setFinishTriggeredAt(s.is_finish_triggered ? s.finish_triggered_at : null);
        }).catch(() => {});
      };

      ws.onclose = () => {
        clearInterval(pingInterval);
        if (mounted) reconnectTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws?.close();
    }

    connect();
    return () => {
      mounted = false;
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      ws?.close();
    };
  }, []);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = toastIdRef.current++;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000);
  };

  const handleRunStarted = (run: Run) => showToast(`✓ Run started for car #${run.car?.number}`, 'success');
  const handleRunFinished = (run: Run) => showToast(`✓ Run finished (${run.raw_time?.toFixed(3)}s)`, 'success');
  const handleRunUpdated = (_run: Run) => {};
  const handleError = (msg: string) => showToast(msg, 'error');
  const handleSuccess = (msg: string) => showToast(msg, 'success');

  const handleTriggerFinish = async () => {
    try {
      const status = await triggerFinish();
      // WS will push the update, but set optimistically for immediate feedback
      setFinishTriggered(status.is_finish_triggered);
      setFinishTriggeredAt(status.finish_triggered_at);
    } catch (e) { handleError(`Failed to trigger finish: ${e}`); }
  };

  const timingMode = activeEvent?.timing_mode ?? 'human';
  const isRaceSpy = timingMode === 'racespy';

  const tabs: { id: TabType; label: string; show: boolean }[] = [
    { id: 'admin',   label: '⚙️ Admin',           show: true },
    { id: 'staging', label: '📋 Staging',          show: isRaceSpy },
    { id: 'starter', label: '👤 Starter',          show: !isRaceSpy },
    { id: 'finish',  label: '🏁 Finish Worker',    show: !isRaceSpy },
    { id: 'timing',  label: '⏱️ Timing & Scoring', show: true },
  ];

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <header style={{ backgroundColor: '#111827', color: 'white', padding: '14px 20px', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}>
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 24 }}>🏁 Race Wrangler</h1>
            {activeEvent && (
              <p style={{ margin: '2px 0 0', fontSize: 13, color: '#9ca3af' }}>
                {activeEvent.name}
                <span style={{ marginLeft: 8, padding: '1px 6px', borderRadius: 10,
                  background: activeEvent.status === 'active' ? '#065f46' : '#374151', fontSize: 11 }}>
                  {activeEvent.status}
                </span>
                <span style={{ marginLeft: 4, padding: '1px 6px', borderRadius: 10, background: '#1e3a8a', fontSize: 11 }}>
                  {timingMode}
                </span>
              </p>
            )}
          </div>
          {!activeEvent && (
            <p style={{ margin: 0, color: '#d97706', fontSize: 13 }}>⚠ No event selected — go to Admin</p>
          )}
        </div>
      </header>

      <div className="container" style={{ paddingTop: 16 }}>
        <nav className="nav-tabs">
          {tabs.filter(t => t.show).map(t => (
            <button key={t.id} className={activeTab === t.id ? 'active' : ''} onClick={() => setActiveTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <main className="container" style={{ minHeight: 'calc(100vh - 180px)', paddingBottom: 40 }}>
        {activeTab === 'admin' && (
          <AdminUI
            activeEvent={activeEvent}
            onEventChange={setActiveEvent}
            onError={handleError}
            onSuccess={handleSuccess}
          />
        )}
        {activeTab === 'staging' && (
          <StagingUI activeEvent={activeEvent} onError={handleError} onSuccess={handleSuccess} />
        )}
        {activeTab === 'starter' && (
          <StarterUI onRunStarted={handleRunStarted} onError={handleError} />
        )}
        {activeTab === 'finish' && (
          <FinishWorkerUI
            finishTriggered={finishTriggered}
            finishTriggeredAt={finishTriggeredAt}
            onRunFinished={handleRunFinished}
            onError={handleError}
            onTriggerFinish={handleTriggerFinish}
          />
        )}
        {activeTab === 'timing' && (
          <TimingAndScoringUI activeEvent={activeEvent} onRunUpdated={handleRunUpdated} onError={handleError} />
        )}
      </main>

      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast ${toast.type}`}>{toast.message}</div>
        ))}
      </div>
    </div>
  );
}

export default App;
