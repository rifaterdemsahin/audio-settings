# macOS Video Production Audio Settings

Automated configuration, diagnostic, and profile management suite for audio settings on Apple Mac mini video production workstations.

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
- Primary Input: `Elgato Wave:3`
- System Alerts: `Scarlett 2i2 USB`
- Input Gain: `85%`

### Run System Health Check ("Doctor")
```bash
./audio.sh doctor
```
Audits:
- `switchaudio-osx` CLI availability
- `ffmpeg` multimedia framework availability
- `coreaudiod` CPU usage and status
- Detection of all physical hardware interfaces
- Sample rate consistency check (identifies 48 kHz vs 96 kHz mismatches)

### Test Audio Output
```bash
./audio.sh test-output
```
Plays a test chime through the currently active output device to verify speaker/headphone sound.

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
| **`studio`** | `Scarlett 2i2 USB` | `Elgato Wave:3` | **Default Video Production**: Mic = Elgato Wave:3, Output = Scarlett monitors/headphones. |
| **`scarlett`** | `Scarlett 2i2 USB` | `Scarlett 2i2 USB` | **All-Focusrite**: Mic plugged into Scarlett XLR channel 1/2, Output = Scarlett monitors. |
| **`wavelink`** | `Scarlett 2i2 USB` | `Wave Link Stream` | **Streaming/Submix**: Uses Elgato Wave Link software mixer routing. |
| **`macmini`** | `Mac mini Speakers` | `Elgato Wave:3` | **Fallback**: Direct internal Mac mini chassis speaker output. |
| **`monitor`** | `LG HDR 4K` | `Elgato Wave:3` | **Display Audio**: Routes output to the LG 4K display. |

---

## 5. Troubleshooting & Maintenance

### If Audio Freezes or CoreAudio Daemon Hangs
If a wireless device or USB unplug causes CoreAudio to become unresponsive:
```bash
sudo killall coreaudiod
```
macOS `launchd` will automatically restart the audio daemon cleanly within 2 seconds without requiring a reboot.

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

---

## 6. Verification Log

- **Output Verification**: Tested via `afplay /System/Library/Sounds/Ping.aiff` on `Scarlett 2i2 USB` (passed).
- **Input Verification**: Tested via `ffmpeg -f avfoundation` on `Elgato Wave:3` (captured 49,230 bytes) and `Scarlett 2i2 USB` (captured 339,022 bytes with signal detected at `-21.0 dB`).
# cursor-agent-repo
