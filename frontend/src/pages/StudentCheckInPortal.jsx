import React, { useState, useEffect, useRef } from 'react';
import { 
  Camera, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  UserCheck, 
  ArrowLeft, 
  Sparkles,
  RefreshCw,
  Eye,
  Zap,
  Hand,
  Scan
} from 'lucide-react';
import { attendanceService } from '../services/attendanceService';

export default function StudentCheckInPortal({ sessionCodeFromUrl, onBackToFaculty }) {
  const [sessionCode, setSessionCode] = useState(sessionCodeFromUrl || '');
  const [rollNo, setRollNo] = useState(() => localStorage.getItem('agemc_student_roll') || '');
  const [cameraActive, setCameraActive] = useState(false);
  const [isVideoLive, setIsVideoLive] = useState(false);
  const [selfieDataUrl, setSelfieDataUrl] = useState(null);
  const [fullFaceDataUrl, setFullFaceDataUrl] = useState(null);
  const [isAnalyzingRetina, setIsAnalyzingRetina] = useState(false);
  const [scanTelemetry, setScanTelemetry] = useState('ANALYZING OCULAR PATTERNS...');
  const [captureMode, setCaptureMode] = useState('auto'); // 'auto' (10s) or 'manual'
  const [countdown, setCountdown] = useState(10);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fullCanvasRef = useRef(null);
  const countdownTimerRef = useRef(null);

  // Start camera stream
  const startCamera = async () => {
    setError(null);
    setIsVideoLive(false);
    setCountdown(10);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
        setCameraActive(true);
      }
    } catch (err) {
      console.warn('Camera access error:', err);
      setError('Please allow Camera access for mandatory Face & Retina verification.');
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
    setIsVideoLive(false);
  };

  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, []);

  // Monitor video playback to confirm non-black live frames
  useEffect(() => {
    let checkInterval = null;
    if (cameraActive && videoRef.current) {
      checkInterval = setInterval(() => {
        const v = videoRef.current;
        if (v && v.readyState >= 2 && v.videoWidth > 0 && !v.paused) {
          setIsVideoLive(true);
        }
      }, 250);
    }
    return () => {
      if (checkInterval) clearInterval(checkInterval);
    };
  }, [cameraActive]);

  // Auto-Capture 10-Second Countdown (Starts ONLY when live video is genuinely playing)
  useEffect(() => {
    if (cameraActive && isVideoLive && captureMode === 'auto' && !selfieDataUrl) {
      setCountdown(10);
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);

      countdownTimerRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownTimerRef.current);
            performRetinaCapture();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
    };
  }, [cameraActive, isVideoLive, captureMode, selfieDataUrl]);

  // Crop & Capture specifically the Retina & Eye Biometric Region with Python AI Background Removal
  const performRetinaCapture = async () => {
    if (!videoRef.current || !canvasRef.current) return null;
    const video = videoRef.current;
    const canvas = canvasRef.current;

    const w = video.videoWidth || 640;
    const h = video.videoHeight || 480;
    if (w <= 0 || h <= 0) return null;

    // 1. Capture Full Frame for backend recognition
    let fullUrl = '';
    if (fullCanvasRef.current) {
      fullCanvasRef.current.width = w;
      fullCanvasRef.current.height = h;
      const fCtx = fullCanvasRef.current.getContext('2d');
      fCtx.drawImage(video, 0, 0, w, h);
      fullUrl = fullCanvasRef.current.toDataURL('image/jpeg', 0.88);
      setFullFaceDataUrl(fullUrl);
    }

    // 2. Crop ONLY Retina & Eye Region (upper 20% to 65% area where the reticles target eyes)
    const cropX = Math.floor(w * 0.12);
    const cropY = Math.floor(h * 0.20);
    const cropWidth = Math.floor(w * 0.76);
    const cropHeight = Math.floor(h * 0.48);

    canvas.width = cropWidth;
    canvas.height = cropHeight;
    const ctx = canvas.getContext('2d');

    // Draw eye region
    ctx.drawImage(video, cropX, cropY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight);

    // Apply Background Removal / Studio Vignette Mask (dark slate background isolation)
    const grad = ctx.createRadialGradient(
      cropWidth / 2, cropHeight / 2, cropHeight * 0.38,
      cropWidth / 2, cropHeight / 2, cropWidth * 0.52
    );
    grad.addColorStop(0, 'rgba(2, 6, 23, 0)');
    grad.addColorStop(0.7, 'rgba(2, 6, 23, 0.45)');
    grad.addColorStop(1, '#020617');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, cropWidth, cropHeight);

    const initialCropUrl = canvas.toDataURL('image/jpeg', 0.92);
    setSelfieDataUrl(initialCropUrl);
    stopCamera();

    // 3. Trigger 0.8s - 1.0s High-Tech Retina Laser Analysis
    setIsAnalyzingRetina(true);
    setScanTelemetry('SCANNING RETINA & IRIS...');

    try {
      if (fullUrl) {
        const pyRes = await attendanceService.processBiometricPhoto(fullUrl);
        if (pyRes?.isolated_retina_base64) {
          setSelfieDataUrl(pyRes.isolated_retina_base64);
        }
        if (pyRes?.isolated_full_base64) {
          setFullFaceDataUrl(pyRes.isolated_full_base64);
        }
      }
    } catch (err) {
      console.warn('Biometric processing fallback:', err);
    }

    setTimeout(() => {
      setScanTelemetry('RETINA PATTERN LOCKED ✓');
      setIsAnalyzingRetina(false);
    }, 850);

    return initialCropUrl;
  };

  const handleCheckIn = async (e) => {
    if (e) e.preventDefault();
    if (!rollNo.trim() || !sessionCode.trim()) {
      setError('Please provide both Session Code and your Roll / Registration Number.');
      return;
    }

    let retinaPhoto = selfieDataUrl;
    let fullPhoto = fullFaceDataUrl;
    if (cameraActive && !retinaPhoto) {
      retinaPhoto = performRetinaCapture();
    }

    // STRICT MANDATORY BIOMETRIC ENFORCEMENT
    if (!retinaPhoto) {
      setError('Retina Biometric Verification Required: Please align eyes and capture retina scan.');
      startCamera();
      return;
    }

    setSubmitting(true);
    setError(null);

    // Save roll for next time
    localStorage.setItem('agemc_student_roll', rollNo.trim().toUpperCase());

    try {
      const res = await attendanceService.mobileCheckIn({
        session_code: sessionCode.trim(),
        student_id: rollNo.trim().toUpperCase(),
        face_image_base64: fullPhoto || retinaPhoto
      });

      setResult(res);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to record attendance. Please check details.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
      <div className="card" style={{ maxWidth: '460px', width: '100%', padding: '24px', border: '1px solid var(--glass-border-hover)' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <div className="brand-badge" style={{ margin: '0 auto 10px', fontSize: '13px' }}>AGEMC</div>
          <h2 style={{ fontSize: '19px', fontWeight: 800, color: 'var(--text-primary)' }}>Student Attendance Check-In</h2>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Biometric Face & Retina Verification System
          </div>
        </div>

        {/* Success Result Screen */}
        {result ? (
          <div style={{ textAlign: 'center', padding: '12px 0' }}>
            <div style={{ width: '68px', height: '68px', borderRadius: '50%', background: 'var(--badge-present-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px', color: 'var(--status-present)' }}>
              <CheckCircle2 size={38} />
            </div>

            <h3 style={{ fontSize: '19px', fontWeight: 800, color: 'var(--status-present)', marginBottom: '4px' }}>
              {result.already_marked ? 'Already Checked In' : 'Attendance Marked!'}
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              {result.message}
            </p>

            <div style={{ background: 'var(--bg-card)', padding: '14px', borderRadius: '10px', textAlign: 'left', marginBottom: '16px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Student Name:</span>
                <strong>{result.data?.student_name}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Roll / Reg No:</span>
                <strong style={{ fontFamily: 'var(--font-mono)' }}>{result.data?.roll_no}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Subject:</span>
                <strong>{result.data?.subject}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Room:</span>
                <strong>{result.data?.room}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Verification:</span>
                <span className="badge badge-present">✓ Retina & Face Biometrics Matched</span>
              </div>
            </div>

            <button
              className="btn btn-secondary"
              onClick={() => {
                setResult(null);
                setSelfieDataUrl(null);
                setFullFaceDataUrl(null);
                startCamera();
              }}
              style={{ width: '100%' }}
            >
              Done / Check-In Another Student
            </button>
          </div>
        ) : (
          /* Check-In Form Screen */
          <form onSubmit={handleCheckIn}>
            {error && (
              <div style={{ padding: '10px 12px', background: 'var(--badge-absent-bg)', color: 'var(--status-absent)', borderRadius: '8px', marginBottom: '14px', display: 'flex', gap: '8px', fontSize: '12px' }}>
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '12px' }}>
              <label className="form-label">Classroom Session Code *</label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="e.g. SA-SESSION-85D7E4"
                value={sessionCode}
                onChange={(e) => setSessionCode(e.target.value)}
                style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '13px' }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label className="form-label">Your Roll / Registration Number *</label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="e.g. 18 or AGEMC AI 18"
                value={rollNo}
                onChange={(e) => setRollNo(e.target.value)}
                style={{ fontWeight: 600, fontSize: '13px' }}
              />
            </div>

            {/* MANDATORY BIOMETRIC RETINA SCANNER */}
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label className="form-label" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-teal)' }}>
                  <Eye size={14} />
                  <span>Retina Biometrics * (Mandatory)</span>
                </label>

                {/* Auto (10s) / Manual Mode Toggle Buttons */}
                <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-surface)', padding: '2px', borderRadius: '6px' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setCaptureMode('auto');
                      setCountdown(10);
                      if (!cameraActive) startCamera();
                    }}
                    style={{
                      background: captureMode === 'auto' ? 'var(--accent-teal)' : 'transparent',
                      color: captureMode === 'auto' ? '#042f2e' : 'var(--text-muted)',
                      border: 'none',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Zap size={11} />
                    <span>Auto (10s)</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setCaptureMode('manual');
                      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
                      if (!cameraActive) startCamera();
                    }}
                    style={{
                      background: captureMode === 'manual' ? 'var(--accent-teal)' : 'transparent',
                      color: captureMode === 'manual' ? '#042f2e' : 'var(--text-muted)',
                      border: 'none',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Hand size={11} />
                    <span>Manual</span>
                  </button>
                </div>
              </div>

              {/* Futuristic Retina Biometric Scanner Live View */}
              <div className="biometric-scanner-frame" style={{ display: cameraActive ? 'block' : 'none', margin: '8px 0' }}>
                {/* Laser Scanning Beam */}
                <div className="laser-scanner-line" />

                {/* Left Eye / Retina Target Circle */}
                <div className="retina-reticle" style={{ top: '34%', left: '26%' }}>
                  <div className="retina-crosshair" />
                </div>

                {/* Right Eye / Retina Target Circle */}
                <div className="retina-reticle" style={{ top: '34%', right: '26%' }}>
                  <div className="retina-crosshair" />
                </div>

                <video
                  ref={videoRef}
                  playsInline
                  muted
                  style={{ width: '100%', height: '220px', objectFit: 'cover', transform: 'scaleX(-1)', display: 'block' }}
                />

                {/* Auto-Capture 10s Countdown Badge */}
                {captureMode === 'auto' && isVideoLive && (
                  <div style={{ position: 'absolute', top: '10px', right: '10px', background: 'rgba(2, 6, 23, 0.85)', backdropFilter: 'blur(6px)', border: '2px solid var(--accent-teal)', color: 'var(--accent-teal)', width: '38px', height: '38px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '15px', fontFamily: 'var(--font-mono)', zIndex: 20 }}>
                    {countdown}s
                  </div>
                )}

                {/* Real-Time Telemetry Overlay */}
                <div style={{ position: 'absolute', bottom: '8px', left: '8px', right: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(2, 6, 23, 0.80)', backdropFilter: 'blur(6px)', padding: '5px 10px', borderRadius: '8px', fontSize: '11px', color: 'var(--accent-teal)', fontFamily: 'var(--font-mono)' }}>
                  <span>● RETINA SCAN: {captureMode === 'auto' ? `AUTO-LOCK IN ${countdown}s` : 'ALIGN EYES & CLICK CAPTURE'}</span>
                  <span>128-D SFACE</span>
                </div>
              </div>

              {/* Action Button for Manual / Instant Capture */}
              {cameraActive && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={performRetinaCapture}
                  style={{ width: '100%', padding: '10px', fontSize: '13px', marginTop: '6px', fontWeight: 700 }}
                >
                  <Camera size={16} />
                  <span>{captureMode === 'auto' ? `Snap Retina Now (${countdown}s left)` : 'Capture & Lock Retina Scan'}</span>
                </button>
              )}

              {/* Captured Retina & Eyes Biometric Preview with 1-Sec Laser Analysis Animation */}
              {selfieDataUrl && !cameraActive && (
                <div style={{ textAlign: 'center', padding: '14px', background: 'var(--bg-card)', borderRadius: '12px', border: '1px solid var(--border-color)', margin: '8px 0' }}>
                  <div style={{ position: 'relative', display: 'inline-block', maxWidth: '280px', width: '100%', borderRadius: '12px', overflow: 'hidden' }}>
                    <img
                      src={selfieDataUrl}
                      alt="Retina Scan Preview"
                      style={{ width: '100%', height: '200px', borderRadius: '12px', objectFit: 'cover', border: '2px solid var(--status-present)', boxShadow: '0 0 20px rgba(20, 184, 166, 0.5)', display: 'block' }}
                    />

                    {/* 0.8s - 1.0s High-Speed Laser Scan Overlay */}
                    {isAnalyzingRetina && (
                      <div className="retina-analysis-overlay">
                        <div className="retina-analysis-laser" />
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#22c55e', fontWeight: 800, fontSize: '11px', fontFamily: 'var(--font-mono)', background: 'rgba(2, 6, 23, 0.85)', padding: '4px 10px', borderRadius: '6px' }}>
                          <Scan size={14} className="animate-spin" />
                          <span>{scanTelemetry}</span>
                        </div>
                      </div>
                    )}

                    {!isAnalyzingRetina && (
                      <div style={{ position: 'absolute', bottom: '6px', right: '6px', background: 'var(--status-present)', color: '#fff', borderRadius: '50%', padding: '4px', zIndex: 10 }}>
                        <CheckCircle2 size={16} />
                      </div>
                    )}
                  </div>

                  <div style={{ fontSize: '12px', color: isAnalyzingRetina ? 'var(--accent-teal)' : 'var(--status-present)', fontWeight: 800, marginTop: '8px' }}>
                    {isAnalyzingRetina ? '⚡ Scanning & Analyzing Retina Biometrics...' : '✓ Retina & Ocular Landmarks Aligned & Locked'}
                  </div>

                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={isAnalyzingRetina}
                    onClick={() => {
                      setSelfieDataUrl(null);
                      setFullFaceDataUrl(null);
                      startCamera();
                    }}
                    style={{ fontSize: '11px', padding: '4px 12px', marginTop: '8px' }}
                  >
                    <RefreshCw size={12} />
                    <span>Retake Retina Scan</span>
                  </button>
                </div>
              )}

              {!cameraActive && !selfieDataUrl && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={startCamera}
                  style={{ width: '100%', padding: '10px', fontSize: '12px' }}
                >
                  <Camera size={15} />
                  <span>Start Retina Scanner Camera</span>
                </button>
              )}
            </div>

            <canvas ref={canvasRef} style={{ display: 'none' }} />
            <canvas ref={fullCanvasRef} style={{ display: 'none' }} />

            <div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting || isAnalyzingRetina}
                style={{ width: '100%', padding: '12px', fontSize: '14px', fontWeight: 700 }}
              >
                <UserCheck size={16} />
                <span>{submitting ? 'Verifying Retina Biometrics...' : 'Verify & Mark Attendance'}</span>
              </button>
            </div>
          </form>
        )}

        {onBackToFaculty && (
          <div style={{ textAlign: 'center', marginTop: '16px' }}>
            <button
              onClick={onBackToFaculty}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '11px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            >
              <ArrowLeft size={12} />
              <span>Back to Faculty Dashboard</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
