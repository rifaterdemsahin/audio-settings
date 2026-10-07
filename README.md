# macOS Video Production Audio Settings

Automated configuration, diagnostic, and profile management suite for audio settings on Apple Mac mini video production workstations.

> [!NOTE]
> For the comprehensive diagnostic analysis explaining the 1-second audio cutout issue (CoreAudio Error `-66681` and Wave Link locks), read the full [Diagnostic & Failure Analysis Report](REPORT.md).

---

## 1. Problem Overview & Diagnosis

When audio settings were reported as "not working" on this Mac mini, our diagnostics revealed four specific root causes:

| Root Cause | Initial State | Consequence | Fixed State |
| :--- | :--- | :--- | :--- |
| **Output Device Routing** | `Mac mini Speakers` | Audio was playing through the tinny internal Mac mini chassis speaker instead of connected studio monitors or headphones. | `Scarlett 2i2 USB` |
| **Input Device Routing** | `Wave Link Stream` (Virtual) | Apps (OBS, QuickTime, Browser, Teams) were listening to the virtual software capture stream which had no active audio mix. | `Elgato Wave:3` (Physical Mic) |
| **Software Gain Level** | Input volume set to `38%` | Microphone recordings were excessively quiet or inaudible. | Raised to `85%` |
| **Sample Rate Mismatch** | Virtual mix at `96,000 Hz`, hardware at `48,000 Hz` | Potential audio buffer desync, sample rate conversion overhead, and audio dropouts in video production. | Flagged in `doctor` & unified to `48,000 Hz` |
| **Continuity Device Probe Latency** | Wireless `StudioiPhone14 Microphone` | CoreAudio HAL queries hung for 2+ minutes attempting to negotiate with sleeping/distant iPhone over wireless Continuity. | Bypassed by targeting direct USB hardware |

---

## 2. Detected Audio Hardware & Topology

```
+-------------------------------------------------------------+
|                     Mac mini Workstation                     |
+-------------------------------------------------------------+
        |                                       |
        | USB                                   | USB
        v                                       v
+-----------------------+              +-----------------------+
|   Scarlett 2i2 USB    |              |     Elgato Wave:3     |
| (Focusrite Interface) |              |   (Condenser Mic)     |
| 2 In / 2 Out @ 48 kHz |              | 1 In / 2 Out @ 48 kHz |
|  -> Studio Monitors   |              |  -> Direct Voice      |
|  -> Headphones        |              +-----------------------+
+-----------------------+                         |
        ^                                         v
        | Output                         +-------------------+
        +--------------------------------|  Wave Link Mix    |
                                         | (Optional 96 kHz) |
                                         +-------------------+
```

- **Output Destination**: **Scarlett 2i2 USB** (48,000 Hz) — Controls studio monitors and primary headphone feed with physical volume knobs.
- **Input Source**: **Elgato Wave:3** (48,000 Hz) — Studio condenser microphone for voiceover and video production.
- **Fallback Output**: **Mac mini Speakers** (48,000 Hz internal) and **LG HDR 4K** (48,000 Hz DisplayPort).

---

## 3. Quick Start & CLI Usage

A unified CLI `audio.sh` (or `audio_settings.py`) is provided in this repository.

### Check Current Audio Status
```bash
./audio.sh status
```
Outputs the active output, input, system alert device, and all detected devices.

### Apply Recommended Video Production Settings ("One-Click Fix")
```bash
./audio.sh fix
```
Automatically configures:
- Primary Output: `Scarlett 2i2 USB`
- Primary Input: `Wave Link Stream` (when Wave Link is running) or `Elgato Wave:3`
- System Alerts: `Scarlett 2i2 USB`
- Input Gain: `85%`

### Refresh Browser Audio & Fix 10-Second Cutouts
```bash
./audio.sh fix-browser
```
Terminates stale browser audio helper workers (`Google Chrome Helper AudioService`), resets CoreAudio buffer channels, and cleanly rebinds playback to `Scarlett 2i2 USB`.

### Run System Health Check ("Doctor")
```bash
./audio.sh doctor
```
Audits:
- `switchaudio-osx` CLI availability
- `ffmpeg` multimedia framework availability
- `coreaudiod` CPU usage and status
- Elgato Wave Link app status and hardware lock detection
- Detection of all physical hardware interfaces
- Sample rate consistency check (identifies 48 kHz vs 96 kHz mismatches)

### Test Audio Output
```bash
# Play short 1.5s system chime
./audio.sh test-output

# Play continuous 6-second multi-frequency test melody
./audio.sh test-output --continuous

# Test specific hardware destination
./audio.sh test-device "Scarlett 2i2 USB"
./audio.sh test-device "Mac mini Speakers"
./audio.sh test-device "LG HDR 4K"
```

### Test Microphone Recording
```bash
./audio.sh test-input
```
Records a 2-second audio sample from the active input device, computes peak and mean volume decibels (`volumedetect`), and validates audio capture.

---

## 4. Audio Profiles

Switch between setups with a single command:

```bash
./audio.sh profile <name>
```

| Profile | Output Device | Input Device | Purpose |
| :--- | :--- | :--- | :--- |
| **`studio`** | `Scarlett 2i2 USB` | `Wave Link Stream` / `Elgato Wave:3` | **Default Video Production**: Wave Link virtual mic (or Wave:3), Output = Scarlett monitors/headphones. |
| **`scarlett`** | `Scarlett 2i2 USB` | `Scarlett 2i2 USB` | **All-Focusrite**: Mic plugged into Scarlett XLR channel 1/2, Output = Scarlett monitors. |
| **`wavelink`** | `Scarlett 2i2 USB` | `Wave Link Stream` | **Streaming/Submix**: Uses Elgato Wave Link software mixer routing. |
| **`macmini`** | `Mac mini Speakers` | `Wave Link Stream` / `Scarlett` | **Fallback**: Direct internal Mac mini chassis speaker output. |
| **`monitor`** | `LG HDR 4K` | `Wave Link Stream` / `Scarlett` | **Display Audio**: Routes output to the LG 4K display. |

---

## 5. Comprehensive Fixes Inventory

1. **Fix 1: Output Destination Correction**  
   Switched system default output from low-quality built-in `Mac mini Speakers` to the studio `Scarlett 2i2 USB` DAC.
2. **Fix 2: Elgato Wave Link Hardware Lock & Error `-66681` Prevention**  
   Detected background `WaveLinkMacOS` process. Guarded output switching to prevent sending audio directly to physical `Elgato Wave:3` (which triggers `AudioQueueStart (-66681)` and drops audio after 1 second). Dynamically mapped mic input to `Wave Link Stream`.
3. **Fix 3: Input Gain Calibration**  
   Programmatically raised software input gain from an attenuated `38%` to optimal `85%`.
4. **Fix 4: Continuous Multi-Tone Testing**  
   Added `assets/test_tone_6s.wav` and `./audio.sh test-output --continuous` to replace the ambiguous 1.5-second `Ping.aiff` chime.
5. **Fix 5: 10-Second Cutout Resolution (`fix-browser` & USB Clock Drift)**  
   Diagnosed `libAudioIssueDetector` (-120 dB silence) and `usbaudiod` microframe timestamp drift. Created `./audio.sh fix-browser` to flush stale Chrome audio helper workers and rebind audio contexts cleanly.
6. **Fix 6: Interactive Web Dashboard & GitHub Pages Deployment**  
   Created `index.html` with an embedded Web Audio API player, continuous tone loop mode, live frequency visualizer, and diagnostics summary.

---

## 6. Troubleshooting & Maintenance

### If Audio Freezes or CoreAudio Daemon Hangs
If a wireless device or USB unplug causes CoreAudio to become unresponsive or microframe clock drift accumulates:
```bash
sudo killall coreaudiod
```
macOS `launchd` will automatically restart both `coreaudiod` and `usbaudiod` cleanly within 2 seconds without requiring a reboot.

### If Audio Cuts Out in Web Browser (Chrome/Safari)
```bash
./audio.sh fix-browser
```

### Sample Rates for Video Production (48 kHz Standard)
In professional video production (OBS, DaVinci Resolve, Final Cut Pro, Premiere):
- Standard sample rate is **48,000 Hz (48 kHz)**.
- If **Wave Link Stream** is configured at `96,000 Hz` while **Scarlett** is at `48,000 Hz`, open:
  `/Applications/Utilities/Audio MIDI Setup.app`
  and set the Format for all devices to **48,000 Hz**.

### Continuity Camera/Microphone Stall
If an iPhone is paired via Continuity Camera (`StudioiPhone14`), CoreAudio queries may stall if the phone is asleep or out of range. 
To disable Continuity Camera if not needed:
`System Settings` -> `General` -> `AirPlay & Continuity` -> toggle off **Continuity Camera**.
