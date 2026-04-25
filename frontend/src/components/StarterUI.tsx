import { useState, useRef, useEffect } from 'react';
import { getCars, getHoldStatus, getRuns, startRun, Car, Run } from '../services/api';
import { attachStreamToVideo, openPreferredCamera, stopMediaStream } from '../utils/camera';

interface StarterUIProps {
  onRunStarted: (run: Run) => void;
  onError: (message: string) => void;
}

export function StarterUI({ onRunStarted, onError }: StarterUIProps) {
  const [cars, setCars] = useState<Car[]>([]);
  const [selectedCar, setSelectedCar] = useState<Car | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [holdMessage, setHoldMessage] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Filtered list: all cars when no search term, otherwise filtered
  const visibleCars = searchTerm
    ? cars.filter(car =>
        car.number.toLowerCase().includes(searchTerm.toLowerCase()) ||
        car.model.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : cars;

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
        // Restore display label if a car is selected
        if (selectedCar) setSearchTerm('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [selectedCar]);

  // Load cars on mount
  useEffect(() => {
    loadCars();
  }, []);

  // Poll active runs to detect missed-trip hold state across devices.
  useEffect(() => {
    const checkHoldState = async () => {
      try {
        const [holdStatus, activeRuns] = await Promise.all([getHoldStatus(), getRuns('active')]);
        const flaggedRun = activeRuns.find(run => run.is_missed_trip);
        if (!holdStatus.is_start_held) {
          setHoldMessage(null);
        } else if (flaggedRun) {
          setHoldMessage(`HOLD START - Car #${flaggedRun.car?.number || flaggedRun.car_id} missed a trip. Wait for lights to recover.`);
        } else {
          setHoldMessage('HOLD START - Timing has starts paused. Wait for release.');
        }
      } catch {
        // Ignore transient polling errors to avoid noisy UI.
      }
    };

    checkHoldState();
    const interval = setInterval(checkHoldState, 2000);
    return () => clearInterval(interval);
  }, []);

  async function loadCars() {
    try {
      const fetchedCars = await getCars();
      setCars(fetchedCars);
    } catch (error) {
      onError(`Failed to load cars: ${error}`);
    }
  }

  // Open dropdown and clear filter input so user types fresh
  const openDropdown = () => {
    setSearchTerm('');
    setShowDropdown(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const startCamera = async (showErrorToast = false) => {
    if (!videoRef.current) return;
    setCameraReady(false);
    setCameraError(null);
    stopMediaStream(streamRef.current);
    streamRef.current = null;

    try {
      const stream = await openPreferredCamera();
      streamRef.current = stream;
      await attachStreamToVideo(videoRef.current, stream);
      setCameraReady(true);
    } catch {
      setCameraReady(false);
      setCameraError('Live preview unavailable. Use camera upload, or tap Retry Camera.');
      if (showErrorToast) {
        onError('Live camera preview unavailable. Use camera upload for this device/network.');
      }
    }
  };

  // Initialize webcam
  useEffect(() => {
    startCamera(false);

    return () => {
      stopMediaStream(streamRef.current);
      streamRef.current = null;
      setCameraReady(false);
    };
  }, []);

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = ev => {
      setPhoto(file);
      setPhotoPreview(ev.target?.result as string);
    };
    reader.readAsDataURL(file);

    if (uploadRef.current) uploadRef.current.value = '';
  };

  // Select car from dropdown
  const selectCar = (car: Car) => {
    setSelectedCar(car);
    setSearchTerm('');
    setShowDropdown(false);
  };

  // Capture photo from webcam
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const context = canvasRef.current.getContext('2d');
    if (!context) return;

    canvasRef.current.width = videoRef.current.videoWidth;
    canvasRef.current.height = videoRef.current.videoHeight;
    context.drawImage(videoRef.current, 0, 0);

    canvasRef.current.toBlob(blob => {
      if (blob) {
        const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
        setPhoto(file);
        setPhotoPreview(canvasRef.current!.toDataURL('image/jpeg'));
      }
    }, 'image/jpeg', 0.95);
  };

  // Submit start run
  const handleStartRun = async () => {
    if (!selectedCar || !photo) {
      onError('Please select a car and take a photo');
      return;
    }

    setLoading(true);
    try {
      const run = await startRun(selectedCar.id, photo);
      onRunStarted(run);
      // Reset form
      setSelectedCar(null);
      setSearchTerm('');
      setPhoto(null);
      setPhotoPreview(null);
    } catch (error) {
      onError(`Failed to start run: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="starter-container">
      <div className="card">
        <div className="card-header">Starter UI</div>

        {holdMessage && (
          <div className="alert-banner hold" style={{ marginBottom: '16px' }}>
            🔴 {holdMessage}
          </div>
        )}

        {/* Car Selection — filterable dropdown */}
        <div className="mb-2">
          <label htmlFor="car-search">
            <strong>Select Car:</strong>
          </label>
          <div className="starter-search" ref={searchRef}>
            {/* Trigger button shown when dropdown is closed */}
            {!showDropdown ? (
              <button
                type="button"
                className="starter-select-trigger"
                onClick={openDropdown}
              >
                <span>
                  {selectedCar
                    ? <><strong>#{selectedCar.number}</strong> — {selectedCar.model} ({selectedCar.class_name})</>
                    : <span className="starter-select-placeholder">Select a car…</span>
                  }
                </span>
                <span className="starter-select-caret">▾</span>
              </button>
            ) : (
              /* Filter input shown when open */
              <input
                id="car-search"
                ref={inputRef}
                type="text"
                className="starter-select-input"
                placeholder="Type number or model to filter…"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                autoComplete="off"
              />
            )}

            {/* Dropdown list */}
            {showDropdown && (
              <div className="starter-search-dropdown">
                {visibleCars.length > 0 ? (
                  visibleCars.map(car => (
                    <div
                      key={car.id}
                      className={`starter-search-option${selectedCar?.id === car.id ? ' selected' : ''}`}
                      onMouseDown={() => selectCar(car)}
                    >
                      <strong>#{car.number}</strong> — {car.model}
                      <span className="starter-search-class">{car.class_name}</span>
                    </div>
                  ))
                ) : (
                  <div className="starter-search-empty">No cars found</div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Video feed */}
        <div className="video-container">
          <video ref={videoRef} autoPlay playsInline muted />
        </div>

        {cameraError && (
          <div style={{ marginBottom: '10px', fontSize: 13, color: '#92400e', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, padding: '8px 10px' }}>
            {cameraError}
          </div>
        )}

        <button
          className="secondary"
          onClick={() => startCamera(true)}
          style={{ width: '100%', marginBottom: '10px' }}
        >
          Retry Camera
        </button>

        {/* Capture button */}
        <button
          className="primary"
          onClick={capturePhoto}
          disabled={!cameraReady}
          style={{ width: '100%', marginBottom: '10px' }}
        >
          📸 Take Photo
        </button>

        <label className="secondary" style={{ display: 'block', textAlign: 'center', cursor: 'pointer', marginBottom: '10px', padding: '10px 12px' }}>
          📁 Use Camera Upload
          <input ref={uploadRef} type="file" accept="image/*" capture="environment" style={{ display: 'none' }} onChange={handlePhotoUpload} />
        </label>

        {/* Photo preview */}
        {photoPreview && (
          <div>
            <strong>Photo Preview:</strong>
            <img src={photoPreview} alt="Preview" className="photo-preview" />
          </div>
        )}

        {/* Confirm start button */}
        <button
          className="success"
          onClick={handleStartRun}
          disabled={!selectedCar || !photo || loading}
          style={{ width: '100%', marginTop: '16px' }}
        >
          {loading ? <span className="spinner"></span> : '✓ Confirm Start'}
        </button>
      </div>

      {/* Hidden canvas for photo capture */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
}
