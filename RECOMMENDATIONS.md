# macOS Permanent Audio Optimization & Stabilization Guide

**Workstation**: Apple Mac mini  
**Audio Hardware**: Focusrite Scarlett 2i2 USB, Elgato Wave:3, LG HDR 4K Display  
**Target Goal**: Permanent elimination of CoreAudio freezes, 1-second aborts (`-66681`), and 10-second buffer cutouts.

---

## 1. Overview: The Underlying Instability Factors

Through empirical profiling and system log inspection, we identified four structural issues causing audio failures on this workstation:

1. **Obsolete Virtual HAL Plugins**: 6-year-old deprecated drivers (`MSTeamsAudioDevice.driver` from 2020 and `WaveLinkVirtualAudio.driver` from 2020) loaded inside `coreaudiod`.
2. **Wireless Continuity Handshake Latency**: CoreAudio polling `StudioiPhone14 Microphone` over Bluetooth/WiFi, causing 2-to-4-minute HAL query freezes.
3. **USB Isochronous Clock Drift**: Connecting the Scarlett 2i2 through a CalDigit TS4 Thunderbolt dock causing `usbaudiod` microframe timestamp errors (`calcError > 12,000 ns`), dropping audio after 10 seconds.
4. **Exclusive Hardware Lock Collision**: Elgato Wave Link app claiming exclusive ownership of the physical `Elgato Wave:3` microphone, throwing `AudioQueueStart (-66681)` when accessed by CoreAudio.

---

## 2. Action Plan: Step-by-Step Instructions

### Step 1: Remove Obsolete & Conflicting Audio HAL Drivers

**Why**: macOS loads all drivers located in `/Library/Audio/Plug-Ins/HAL/` directly into the `coreaudiod` root daemon at boot. Stale drivers inject unsupported code and block modern CoreAudio calls.

**Drivers to Remove**:
- `MSTeamsAudioDevice.driver` (v2020.42, dated Oct 2020) — Deprecated by Microsoft; modern Teams uses native ScreenCaptureKit and CoreAudio.
- `WaveLinkVirtualAudio.driver` (v1.0.3, dated Dec 2020) — Duplicate legacy driver conflicting with `WaveLink3VirtualAudio.driver` (v1.6, dated Jan 2026).

**Terminal Execution (Backs up and cleans safely)**:
```bash
# 1. Create a safe backup folder
sudo mkdir -p /Library/Audio/Plug-Ins/HAL_Backup

# 2. Move deprecated drivers into backup
sudo mv /Library/Audio/Plug-Ins/HAL/MSTeamsAudioDevice.driver /Library/Audio/Plug-Ins/HAL_Backup/
sudo mv /Library/Audio/Plug-Ins/HAL/WaveLinkVirtualAudio.driver /Library/Audio/Plug-Ins/HAL_Backup/

# 3. Reload CoreAudio subsystem (restarts cleanly in 2 seconds)
sudo killall coreaudiod
```

---

### Step 2: Disable Apple Continuity Microphone

**Why**: When macOS tries to query available microphones, it attempts a wireless handshake with the paired iPhone (`StudioiPhone14`). If the phone is locked, asleep, or out of range, the entire CoreAudio query hangs for up to 4 minutes.

**How to Disable**:
1. Open **System Settings** on your Mac mini.
2. Navigate to **General** -> **AirPlay & Continuity**.
3. Toggle **Continuity Camera** to **OFF**.
4. *(Optional)* In **System Settings -> Bluetooth**, if the iPhone appears as an active audio source, disconnect audio sharing.

---

### Step 3: Connect Focusrite Scarlett 2i2 Directly to the Mac mini

**Why**: The Scarlett 2i2 is currently plugged into the **CalDigit TS4 dock** (`TS4 USB2.0 Hub`). Thunderbolt 4 docks multiplex high-bandwidth DisplayPort video, PCIe data, and USB traffic across a single cable. For real-time isochronous audio DACs, this induces microframe clock jitter (`usbaudiod timestamp calcError ns 12583`). After ~10 seconds of accumulated drift, the audio stream drops to digital silence (`-120 dB RMS`).

**How to Fix**:
1. Unplug the Focusrite Scarlett 2i2 USB cable from the CalDigit TS4 dock.
2. Plug it **directly into one of the rear USB-C or USB-A ports on the Mac mini chassis**.
3. Ensure the cable is plugged firmly and avoids unpowered USB splitters.

---

### Step 4: Hardware Coexistence Strategy (Scarlett 2i2 vs Elgato Wave:3)

You currently have two professional audio devices connected simultaneously:
- **Focusrite Scarlett 2i2 USB**: Hardware audio interface with analog preamps and headphone DAC.
- **Elgato Wave:3**: USB condenser microphone with Elgato Wave Link software mixer.

Choose **one** of the two workflows below:

#### Strategy A: Focusrite Primary Studio Setup (Recommended for Video Production)
If your primary monitors and headphones are plugged into the **Focusrite Scarlett 2i2**:
1. Remove **Elgato Wave Link** from startup items:
   - Go to **System Settings** -> **General** -> **Login Items**.
   - Under *Open at Login*, select **Wave Link** and click the **"-"** (minus) button.
   - Quit the Wave Link app from the menu bar if running.
2. **Benefit**: Without Wave Link running, the `Elgato Wave:3` operates as a standard, class-compliant USB microphone. Both Scarlett output and Wave:3 input function simultaneously with zero exclusive lock errors (`-66681`).

#### Strategy B: Streaming Submix Setup (If You Actively Use Wave Link)
If you require Elgato Wave Link to create separate OBS stream mixes:
1. Open the **Wave Link** app.
2. In the top-right corner, set **Monitor Output** permanently to **`Scarlett 2i2 USB`**.
3. In macOS, set system input to **`Wave Link Stream`** (never directly to `Elgato Wave:3`).
4. Set system output to **`Scarlett 2i2 USB`**.

---

### Step 5: Standardize Sample Rates to 48,000 Hz (48 kHz)

**Why**: 48 kHz is the professional broadcast and video standard (used by OBS, DaVinci Resolve, Final Cut Pro, YouTube). Currently, `Wave Link Stream` is running at 96 kHz while the Focusrite is at 48 kHz, forcing real-time software resampling.

**How to Align**:
1. Open `/Applications/Utilities/Audio MIDI Setup.app`.
2. Select each device in the left sidebar:
   - **Scarlett 2i2 USB**: Format = `48,000 Hz, 2 ch 24-bit`
   - **Elgato Wave:3**: Format = `48,000 Hz, 1 ch 24-bit`
   - **Wave Link Stream**: Format = `48,000 Hz, 2 ch 32-bit float`
   - **Mac mini Speakers**: Format = `48,000 Hz, 2 ch 24-bit`

---

## 3. Post-Optimization Verification Checklist

After applying the recommendations, verify the workstation:

```bash
# 1. Verify audio device routing
./audio.sh status

# 2. Run system doctor audit
./audio.sh doctor

# 3. Test continuous uninterrupted audio playback (6 seconds)
./audio.sh test-output --continuous

# 4. Test microphone capture
./audio.sh test-input
```

Expected Doctor Output:
- `switchaudio-osx`: Installed
- `ffmpeg`: Installed
- `CoreAudio daemon`: Running at 0.0% CPU
- `Hardware Devices`: All detected at `48000 Hz`
- `Output`: Scarlett 2i2 USB (Active)
- `Input`: Elgato Wave:3 or Wave Link Stream (Active)
