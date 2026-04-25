import { useState, useRef, useEffect } from 'react';
import {
  ocrScan, createStagedRun, listStagedRuns, deleteStagedRun,
  listCompetitors,
  type Event, type StagedRun, type Competitor, type OCRScanResult,
} from '../services/api';
import { attachStreamToVideo, openPreferredCamera, stopMediaStream } from '../utils/camera';

interface StagingUIProps {
  activeEvent: Event | null;
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}

type Stage = 'capture' | 'scanning' | 'confirm' | 'done';

function formatTime(ms: number | null): string {
  if (ms === null) return '—';
  const s = ms / 1000;
  return s.toFixed(3) + 's';
}

export function StagingUI({ activeEvent, onError, onSuccess }: StagingUIProps) {
  const [stage, setStage] = useState<Stage>('capture');
  const [capturedImage, setCapturedImage] = useState<string | null>(null); // base64
  const [capturedDataUrl, setCapturedDataUrl] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<OCRScanResult | null>(null);
  const [selectedCompetitorId, setSelectedCompetitorId] = useState<string | null>(null);
  const [staging, setStaging] = useState(false);
  const [serverReachable, setServerReachable] = useState(true);

  const [queue, setQueue] = useState<StagedRun[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [manualSearch, setManualSearch] = useState('');

  const fileRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraAutoStarted, setCameraAutoStarted] = useState(false);

  useEffect(() => {
    if (!activeEvent) return;
    loadQueue();
    loadCompetitors();
    const interval = setInterval(loadQueue, 3000);
    return () => clearInterval(interval);
  }, [activeEvent]);

  async function loadQueue() {
    if (!activeEvent) return;
    try {
      setQueue(await listStagedRuns(activeEvent.id));
      setServerReachable(true);
    } catch {
      setServerReachable(false);
    }
  }

  async function loadCompetitors() {
    if (!activeEvent) return;
    try { setCompetitors(await listCompetitors(activeEvent.id)); } catch (e) { onError(`Failed to load competitors: ${e}`); }
  }

  async function startCamera(silent = false) {
    if (!videoRef.current) return;
    stopMediaStream(streamRef.current);
    streamRef.current = null;

    try {
      const stream = await openPreferredCamera();
      streamRef.current = stream;
      await attachStreamToVideo(videoRef.current, stream);
      setCameraActive(true);
      setCameraAutoStarted(true);
    } catch {
      if (!silent) {
        onError('Unable to open live camera preview. Use Upload Photo to take/select a picture.');
      }
    }
  }

  function stopCamera() {
    stopMediaStream(streamRef.current);
    streamRef.current = null;
    setCameraActive(false);
  }

  useEffect(() => {
    return () => {
      stopMediaStream(streamRef.current);
      streamRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!activeEvent) return;
    if (stage !== 'capture') return;
    if (cameraActive) return;
    if (cameraAutoStarted) return;
    startCamera(true);
  }, [activeEvent, stage, cameraActive, cameraAutoStarted]);

  function captureFromCamera() {
    if (!videoRef.current || !canvasRef.current) return;
    const v = videoRef.current;
    const c = canvasRef.current;
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext('2d')!.drawImage(v, 0, 0);
    const dataUrl = c.toDataURL('image/jpeg', 0.85);
    const base64 = dataUrl.split(',')[1];
    setCapturedImage(base64);
    setCapturedDataUrl(dataUrl);
    stopCamera();
    runOCR(base64);
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async ev => {
      const dataUrl = ev.target?.result as string;
      const base64 = dataUrl.split(',')[1];
      setCapturedImage(base64);
      setCapturedDataUrl(dataUrl);
      runOCR(base64);
    };
    reader.readAsDataURL(file);
    if (fileRef.current) fileRef.current.value = '';
  }

  async function runOCR(base64: string) {
    if (!activeEvent) return;
    setStaging(false); // reset
    setStage('scanning');
    setScanResult(null);
    setSelectedCompetitorId(null);
    try {
      const result = await ocrScan(activeEvent.id, base64);
      setScanResult(result);
      if (result.matched_competitor_id) setSelectedCompetitorId(result.matched_competitor_id);
      setStage('confirm');
    } catch (e) {
      onError(`OCR failed: ${e}`);
      setStage('capture');
    } finally { /* done */ }
  }

  async function stageCompetitor(competitorId: string) {
    if (!activeEvent) return;
    setStaging(true);
    try {
      const created = await createStagedRun(activeEvent.id, competitorId, capturedImage || undefined);
      setQueue(prev => [created, ...prev.filter(r => r.id !== created.id)]);
      const comp = competitors.find(c => c.id === competitorId);
      onSuccess(`Staged: #${comp?.number} ${comp?.class_code} — ${comp?.driver_name}`);
      reset();
      await loadQueue();
    } catch (e) {
      onError(`${e}`);
    } finally {
      setStaging(false);
    }
  }

  async function handleStage() {
    if (!selectedCompetitorId) return;
    await stageCompetitor(selectedCompetitorId);
  }

  function reset() {
    setCameraAutoStarted(false);
    setStage('capture');
    setCapturedImage(null);
    setCapturedDataUrl(null);
    setScanResult(null);
    setSelectedCompetitorId(null);
    setManualSearch('');
  }

  async function handleDeleteRun(run_id: string) {
    if (!activeEvent) return;
    try { await deleteStagedRun(activeEvent.id, run_id); await loadQueue(); }
    catch (e) { onError(`${e}`); }
  }

  const filteredCompetitors = competitors.filter(c => {
    const q = manualSearch.toLowerCase();
    return !q || c.number.includes(q) || c.class_code.toLowerCase().includes(q) || c.driver_name.toLowerCase().includes(q);
  });

  const statusColor = (s: string) => ({ staged: '#fef3c7', running: '#def7ec', finished: '#e0f2fe', dnf: '#fee2e2' }[s] || '#f3f4f6');
  const statusText = (s: string) => ({ staged: '⏳ Staged', running: '🏁 Running', finished: '✅ Done', dnf: '❌ DNF' }[s] || s);

  if (!activeEvent) {
    return <div className="card" style={{ padding: 24, textAlign: 'center', color: '#888' }}>Select an event in Admin to use the staging UI.</div>;
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

      {/* Left: capture + confirm */}
      <div>
        <div className="card">
          <div className="card-header">
            Staging Worker — {activeEvent.name}
            {!serverReachable && <span style={{ marginLeft: 10, fontSize: 12, color: '#dc2626', fontWeight: 'normal' }}>⚠ server unreachable</span>}
          </div>
          <div style={{ padding: 16 }}>

            {stage === 'capture' && (
              <>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <video
                    ref={videoRef}
                    style={{ width: '100%', borderRadius: 6, background: '#000', display: cameraActive ? 'block' : 'none' }}
                    autoPlay
                    playsInline
                    muted
                  />
                  <canvas ref={canvasRef} style={{ display: 'none' }} />
                  {cameraActive && (
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button style={{ flex: 1, padding: '10px', background: '#1a56db', color: 'white', border: 'none', borderRadius: 6, fontSize: 16, cursor: 'pointer' }} onClick={captureFromCamera}>
                        📸 Capture
                      </button>
                      <button style={{ padding: '10px 16px', border: '1px solid #ccc', borderRadius: 6, cursor: 'pointer' }} onClick={stopCamera}>Cancel</button>
                    </div>
                  )}
                </div>

                {!cameraActive && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ fontSize: 13, color: '#6b7280' }}>Opening camera… If it does not appear, retry below.</div>
                    <button style={{ padding: '10px', background: '#f3f4f6', color: '#111827', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, cursor: 'pointer', width: '100%' }}
                      onClick={() => startCamera(false)}>🔄 Retry Camera</button>
                    <label style={{ padding: '10px', background: '#f3f4f6', border: '1px solid #ccc', borderRadius: 6, textAlign: 'center', cursor: 'pointer', fontSize: 14 }}>
                      📁 Upload Photo
                      <input ref={fileRef} type="file" accept="image/*" capture="environment" style={{ display: 'none' }} onChange={handleFileUpload} />
                    </label>
                    <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: 12 }}>
                      <p style={{ fontSize: 13, color: '#555', margin: '0 0 8px' }}>Or select manually:</p>
                      <input placeholder="Search # / class / name" value={manualSearch} onChange={e => setManualSearch(e.target.value)}
                        style={{ width: '100%', padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc', boxSizing: 'border-box' }} />
                      {manualSearch && (
                        <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 4, marginTop: 4 }}>
                          {filteredCompetitors.slice(0, 20).map(c => (
                            <div key={c.id} onClick={() => stageCompetitor(c.id)}
                              style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid #f3f4f6', fontSize: 13 }}
                              onMouseEnter={e => (e.currentTarget.style.background = '#eff6ff')}
                              onMouseLeave={e => (e.currentTarget.style.background = 'white')}>
                              <strong>#{c.number}</strong> {c.class_code} — {c.driver_name}
                              <span style={{ fontSize: 11, color: '#888', marginLeft: 6 }}>{c.car_description}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}

            {stage === 'scanning' && (
              <div style={{ textAlign: 'center', padding: 32 }}>
                {capturedDataUrl && <img src={capturedDataUrl} alt="captured" style={{ width: '100%', borderRadius: 6, marginBottom: 12 }} />}
                <div style={{ fontSize: 16 }}>🔍 Running OCR…</div>
              </div>
            )}

            {stage === 'confirm' && (
              <div>
                {capturedDataUrl && <img src={capturedDataUrl} alt="captured" style={{ width: '100%', borderRadius: 6, marginBottom: 12 }} />}

                {scanResult && (
                  <div style={{ marginBottom: 12, padding: 8, background: '#f9fafb', borderRadius: 6, fontSize: 13, color: '#555' }}>
                    OCR read: <strong>{scanResult.raw_text || '(nothing)'}</strong>
                    {' '}— status: <strong>{scanResult.match_status}</strong>
                  </div>
                )}

                <p style={{ fontWeight: 600, marginBottom: 8 }}>Select competitor:</p>

                {/* Top candidates from OCR */}
                {scanResult?.candidates.map(cand => {
                  const selected = selectedCompetitorId === cand.competitor_id;
                  return (
                    <div key={cand.competitor_id} onClick={() => setSelectedCompetitorId(cand.competitor_id)}
                      style={{ padding: '10px 12px', border: `2px solid ${selected ? '#1a56db' : '#e5e7eb'}`,
                        borderRadius: 6, marginBottom: 6, cursor: 'pointer', background: selected ? '#eff6ff' : 'white' }}>
                      <strong>#{cand.number}</strong> {cand.class_code} — {cand.driver_name}
                      {cand.confidence !== undefined && (
                        <span style={{ float: 'right', fontSize: 12, color: '#888' }}>{(cand.confidence * 100).toFixed(0)}%</span>
                      )}
                    </div>
                  );
                })}

                {/* Manual fallback search */}
                <div style={{ marginTop: 10 }}>
                  <input placeholder="Search manually…" value={manualSearch} onChange={e => setManualSearch(e.target.value)}
                    style={{ width: '100%', padding: '6px 10px', borderRadius: 4, border: '1px solid #ccc', boxSizing: 'border-box', fontSize: 13 }} />
                  {manualSearch && (
                    <div style={{ maxHeight: 150, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 4, marginTop: 4 }}>
                      {filteredCompetitors.slice(0, 15).map(c => (
                        <div key={c.id} onClick={() => { setSelectedCompetitorId(c.id); setManualSearch(''); }}
                          style={{ padding: '6px 12px', cursor: 'pointer', borderBottom: '1px solid #f3f4f6', fontSize: 13,
                            background: selectedCompetitorId === c.id ? '#eff6ff' : 'white' }}>
                          <strong>#{c.number}</strong> {c.class_code} — {c.driver_name}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                  <button style={{ flex: 1, padding: '12px', background: selectedCompetitorId ? '#1a56db' : '#9ca3af',
                    color: 'white', border: 'none', borderRadius: 6, fontSize: 15, cursor: selectedCompetitorId ? 'pointer' : 'default' }}
                    onClick={handleStage} disabled={!selectedCompetitorId || staging}>
                    {staging ? 'Staging…' : '✅ Confirm & Stage'}
                  </button>
                  <button style={{ padding: '12px 16px', border: '1px solid #ccc', borderRadius: 6, cursor: 'pointer' }} onClick={reset}>
                    Retake
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right: queue */}
      <div>
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Run Queue ({queue.length})</span>
            <button
              onClick={loadQueue}
              style={{ padding: '4px 8px', fontSize: 12, borderRadius: 4, border: '1px solid #d1d5db', background: 'white', cursor: 'pointer' }}
            >
              Refresh
            </button>
          </div>
          <div style={{ padding: 12 }}>
            {queue.length === 0 && <p style={{ color: '#888', textAlign: 'center', padding: 16 }}>Queue is empty</p>}
            {queue.map((run, i) => (
              <div key={run.id} style={{ padding: '10px 12px', borderRadius: 6, marginBottom: 8, background: statusColor(run.status), position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontSize: 12, color: '#888', marginRight: 6 }}>#{i + 1}</span>
                    {run.competitor ? (
                      <strong>#{run.competitor.number} {run.competitor.class_code}</strong>
                    ) : <strong>Unknown</strong>}
                    {run.competitor && <span style={{ fontSize: 13, marginLeft: 6, color: '#555' }}>{run.competitor.driver_name}</span>}
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{statusText(run.status)}</span>
                    {run.status === 'staged' && (
                      <button onClick={() => handleDeleteRun(run.id)}
                        style={{ padding: '2px 8px', fontSize: 11, background: '#fee2e2', border: 'none', borderRadius: 4, cursor: 'pointer', color: '#c81e1e' }}>
                        Remove
                      </button>
                    )}
                  </div>
                </div>
                {run.raw_time_s !== null && (
                  <div style={{ marginTop: 4, fontSize: 13 }}>
                    Time: <strong>{formatTime(run.raw_time_s * 1000)}</strong>
                    {run.penalties > 0 && <span style={{ marginLeft: 8, color: '#d97706' }}>+{run.penalties * 2}s ({run.penalties} cone{run.penalties !== 1 ? 's' : ''})</span>}
                    {run.adjusted_time_s !== null && run.penalties > 0 && <span style={{ marginLeft: 8, fontWeight: 600 }}>= {formatTime(run.adjusted_time_s * 1000)}</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
