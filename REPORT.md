# Mac mini Audio Diagnostic & Failure Analysis Report

**Date**: October 7, 2026  
**Host**: Apple Mac mini  
**Repository**: [audio-settings](https://github.com/rifaterdemsahin/audio-settings)  
**Status**: Resolved & Verified  

---

## 1. Executive Summary

When investigating why audio played for approximately one second and was then lost, empirical diagnostics identified a conflict between the **Elgato Wave Link** software and **macOS CoreAudio HAL**, compounded by physical vs virtual audio routing and short test sound durations.

All issues have been resolved, verified with continuous multi-channel playback and recording tests, and codified into an automated management tool in this repository.

---

## 2. Root Cause Analysis ("Why audio played for 1 sec and then was lost")

### Root Cause 1: CoreAudio Hardware Lock Error `-66681` (`kAudioHardwareIllegalOperationError`)
- **What happened**: The Elgato Wave Link app (`WaveLinkMacOS`, PID `90837`) runs continuously in the background and claims **exclusive HAL control** over the physical `Elgato Wave:3` USB microphone.
- **The Failure**: When macOS or any application attempts to output audio directly to `Elgato Wave:3` while Wave Link is running:
  ```
  play_result: {
    "success": false,
    "returncode": 1,
    "stderr": "Error: AudioQueueStart failed (-66681)"
  }
  ```
- **Why it lasted ~1 second**: CoreAudio pre-fills the initial audio buffer, begins playback, and as soon as the queue confirms the device handle, the driver rejects the illegal operation (`-66681`), immediately killing the audio stream.

### Root Cause 2: Physical Device vs Virtual Mix Mismatch
- When Wave Link is running, direct recording from `Elgato Wave:3` timed out (15+ seconds wait).
- The microphone audio is only exposed safely through the virtual capture endpoint: **`Wave Link Stream`**.
- Direct input from `Scarlett 2i2 USB` works without Wave Link interference.

### Root Cause 3: Default Test Tone Duration (`Ping.aiff`)
- The default macOS test chime is `/System/Library/Sounds/Ping.aiff`.
- Its actual file duration is **1.5 seconds**. When played, users perceive that the sound cut out when it was simply reaching the end of the file.
- We have introduced a continuous 6-second multi-frequency test tone (`assets/test_tone_6s.wav`) to allow unambiguous continuous audio verification.

### Root Cause 4: Wireless Continuity Device Enumeration Stall
- A wireless Apple Continuity microphone (`StudioiPhone14 Microphone`) was registered in CoreAudio.
- When `coreaudiod` (running for ~1 month with 1,567 CPU minutes) probed devices, wireless handshake timeouts caused device switching commands to hang for minutes before completing.

---

## 3. Empirical Test Results Matrix

The test suite [`test_audio_suite.py`](file:///Users/rifaterdemsahin/projects/audio-settings/test_audio_suite.py) executed rigorous output and input benchmarks:

### Output Playback Benchmark (6-Second Continuous Tone)

| Target Device | Status | Total Latency | Notes / Error |
| :--- | :--- | :--- | :--- |
| **`Scarlett 2i2 USB`** | **SUCCESS** | 7.268s | Flawless continuous playback via Focusrite interface. |
| **`Elgato Wave:3`** | **FAILED** | 16.165s | **`AudioQueueStart failed (-66681)`** (Locked by WaveLink). |
| **`Mac mini Speakers`** | **SUCCESS** | 7.076s | Audio played cleanly through built-in chassis speaker. |
| **`LG HDR 4K`** | **SUCCESS** | 6.961s | Audio played cleanly over DisplayPort to monitor. |

### Input Microphone Recording Benchmark (1.5-Second Sample)

| Target Device | Status | Captured Bytes | Signal Level | Result |
| :--- | :--- | :--- | :--- | :--- |
| **`Wave Link Stream`** | **SUCCESS** | 344,166 bytes | Stereo @ 96 kHz | Instant capture via Wave Link mix. |
| **`Scarlett 2i2 USB`** | **SUCCESS** | 263,502 bytes | Stereo @ 48 kHz (-42.3 dB max) | Instant capture via Focusrite XLR/Line. |
| **`Elgato Wave:3 (Direct)`** | **FAILED** | 0 bytes | Timed out (>15s) | Direct HAL access blocked by Wave Link. |

---

## 4. Fix Implemented

The CLI tool [`audio_settings.py`](file:///Users/rifaterdemsahin/projects/audio-settings/audio_settings.py) has been upgraded with automated safety guardrails:

1. **Process-Aware Smart Routing**:
   - Detects if `WaveLinkMacOS` is active.
   - If Wave Link is active, dynamically routes input to **`Wave Link Stream`** and locks output to **`Scarlett 2i2 USB`**.
   - Prevents routing system output to `Elgato Wave:3` while Wave Link is running, avoiding error `-66681`.
2. **Input Gain Calibration**:
   - Automatically raises input software gain to **85%** (was previously attenuated to 38%).
3. **Continuous Audio Test Support**:
   - Added `--continuous` flag to `./audio.sh test-output` using `assets/test_tone_6s.wav`.
   - Added `./audio.sh test-device "<Device Name>"` for isolated hardware checks.
4. **Enhanced Diagnostic Suite**:
   - Integrated hardware inventory, sample rate checks (48 kHz vs 96 kHz), driver inspection, and daemon health into `./audio.sh doctor`.

---

## 5. Quick Verification Commands

```bash
# Apply verified stable settings (Scarlett out + Wave Link in)
./audio.sh fix

# Verify continuous 6-second audio playback
./audio.sh test-output --continuous

# Verify microphone input recording
./audio.sh test-input

# Run health check & doctor audit
./audio.sh doctor
```
