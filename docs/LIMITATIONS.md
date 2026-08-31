# SmartAttend-AI: Honest Technical Limitations & Constraints

**Document Purpose**: Transparent technical disclosure for SIH Evaluators and System Engineers.  
**Philosophy**: No overclaims of 100% spoof immunity or perfect accuracy.  

---

## 🔍 1. Computer Vision & Liveness Limitations

1. **Replay Video Playback Attacks**:
   - The multi-signal liveness detector reliably detects static printed photos, paper masks, and static phone screens.
   - However, high-resolution HDR OLED displays playing high-fps pre-recorded video with realistic head movements and eye blinks may present edge-case false passes unless infrared (IR) or depth sensors are paired with the RGB camera.
2. **Extreme Facial Angles & Occlusions**:
   - Detection and recognition accuracy degrades when head yaw/pitch exceeds $\pm 45^\circ$ or when $> 60\%$ of facial features are occluded (e.g. heavy medical masks or deep shadows).
3. **Sub-Optimal Classroom Lighting**:
   - Near-dark environments ($< 10\text{ lux}$) or direct backlighting (e.g. standing directly in front of a sunlit window) reduce detection confidence. Minimum ambient illumination of $\sim 50\text{ lux}$ is recommended.

---

## 🖥️ 2. Hardware & Camera Dependencies

1. **Camera Sensor Quality**:
   - The system requires a minimum camera resolution of $640 \times 480$ with at least $15\text{ FPS}$ capture capability. Extremely low-grade USB webcams with heavy motion blur may delay landmark tracking.
2. **Local Edge Compute**:
   - While optimized to run at $> 100\text{ FPS}$ on multi-core x86 CPUs, running concurrent camera streams across 10+ lecture halls on a single low-power CPU (e.g. Raspberry Pi 4) requires scaled multi-worker deployment or GPU acceleration.

---

## 🔒 3. Authentication & Production Security Limitations

1. **Local Single-Node Deployment**:
   - The current prototype operates as an on-premise local server. Multi-campus synchronization across geographically separated branches requires an encrypted synchronization daemon.
2. **Faculty Authentication & Role-Based Access Control (RBAC)**:
   - The current demo backend validates session tokens and input schemas, but does not enforce multi-tier JWT/OAuth2 login with role permissions (e.g. Dean vs Professor vs TA). This is planned for the enterprise cloud-sync phase.

---

## 📊 4. Analytics & Small-Data Constraints

1. **Minimum Class Session Requirements**:
   - AI risk predictions and trend classifications require at least 3 historical classroom sessions per student. Smaller cohorts trigger `INSUFFICIENT_DATA` mode for safety.
2. **Educational Estimates vs Guarantees**:
   - Risk predictions and missable class margins are mathematical trajectory estimates based on historical records, not infallible future certainties. Excused medical absences cannot be inferred automatically without faculty input.
