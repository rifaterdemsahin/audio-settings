#!/usr/bin/env python3
"""
Audio Settings CLI for macOS (Mac mini Video Production Setup)
Manages audio input/output devices, volume, diagnostics, and profiles.
"""

import sys
import subprocess
import shutil
import argparse
import os
import json
import re

PROFILES = {
    "studio": {
        "description": "Video production standard: Mic = Elgato Wave:3, Out = Scarlett 2i2 USB",
        "output": "Scarlett 2i2 USB",
        "input": "Elgato Wave:3",
        "system": "Scarlett 2i2 USB",
        "input_volume": 85,
    },
    "scarlett": {
        "description": "All Focusrite: Mic = Scarlett 2i2 USB, Out = Scarlett 2i2 USB",
        "output": "Scarlett 2i2 USB",
        "input": "Scarlett 2i2 USB",
        "system": "Scarlett 2i2 USB",
        "input_volume": 85,
    },
    "wavelink": {
        "description": "Wave Link Software Mix: Mic = Wave Link Stream, Out = Scarlett 2i2 USB",
        "output": "Scarlett 2i2 USB",
        "input": "Wave Link Stream",
        "system": "Scarlett 2i2 USB",
        "input_volume": 85,
    },
    "macmini": {
        "description": "Built-in Mac mini fallback: Mic = Elgato Wave:3, Out = Mac mini Speakers",
        "output": "Mac mini Speakers",
        "input": "Elgato Wave:3",
        "system": "Mac mini Speakers",
        "input_volume": 85,
    },
    "monitor": {
        "description": "DisplayPort monitor: Mic = Elgato Wave:3, Out = LG HDR 4K",
        "output": "LG HDR 4K",
        "input": "Elgato Wave:3",
        "system": "Scarlett 2i2 USB",
        "input_volume": 85,
    },
}

def run_cmd(cmd, timeout=15):
    """Run shell command and return stdout string, or None if failed."""
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return res.stdout.strip()
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None

def check_dependencies():
    """Ensure SwitchAudioSource is available."""
    bin_path = shutil.which("SwitchAudioSource")
    if not bin_path:
        print("[!] SwitchAudioSource not found in PATH.")
        print("[*] Attempting to install via Homebrew...")
        subprocess.run(["brew", "install", "switchaudio-osx"], check=False)
        bin_path = shutil.which("SwitchAudioSource")
        if not bin_path:
            print("[x] Error: Please install switchaudio-osx manually: brew install switchaudio-osx")
            sys.exit(1)
    return bin_path

def get_current_devices():
    """Return dict of current output, input, and system audio devices."""
    out = run_cmd(["SwitchAudioSource", "-c", "-t", "output"])
    inp = run_cmd(["SwitchAudioSource", "-c", "-t", "input"])
    sys_dev = run_cmd(["SwitchAudioSource", "-c", "-t", "system"])
    return {
        "output": out or "Unknown",
        "input": inp or "Unknown",
        "system": sys_dev or "Unknown",
    }

def get_available_devices():
    """Return available output and input devices."""
    raw_out = run_cmd(["SwitchAudioSource", "-a", "-t", "output"])
    raw_in = run_cmd(["SwitchAudioSource", "-a", "-t", "input"])
    outputs = [line.strip() for line in raw_out.splitlines() if line.strip()] if raw_out else []
    inputs = [line.strip() for line in raw_in.splitlines() if line.strip()] if raw_in else []
    return outputs, inputs

def get_volume_settings():
    """Query osascript volume settings."""
    out = run_cmd(["osascript", "-e", "get volume settings"])
    return out or "Unavailable"

def get_hardware_info():
    """Fetch hardware device details from system_profiler."""
    raw_json = run_cmd(["system_profiler", "SPAudioDataType", "-json"], timeout=20)
    if not raw_json:
        return {}
    try:
        data = json.loads(raw_json)
        devices = {}
        for group in data.get("SPAudioDataType", []):
            for item in group.get("_items", []):
                name = item.get("_name")
                if name:
                    devices[name] = {
                        "srate": item.get("coreaudio_device_srate"),
                        "manufacturer": item.get("coreaudio_device_manufacturer"),
                        "transport": item.get("coreaudio_device_transport", "").replace("coreaudio_device_type_", ""),
                        "input": item.get("coreaudio_device_input", 0),
                        "output": item.get("coreaudio_device_output", 0),
                    }
        return devices
    except Exception:
        return {}

def set_device(device_name, device_type="output"):
    """Set audio device for output, input, or system."""
    res = subprocess.run(
        ["SwitchAudioSource", "-s", device_name, "-t", device_type],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if res.returncode == 0:
        print(f"  [✓] Set {device_type.capitalize()} -> {device_name}")
        return True
    else:
        print(f"  [!] Failed to set {device_type} to '{device_name}': {res.stderr.strip()}")
        return False

def set_input_volume(level):
    """Set input volume percentage (0-100)."""
    script = f"set volume input volume {level}"
    run_cmd(["osascript", "-e", script])
    print(f"  [✓] Set Input Volume -> {level}%")

def cmd_status(args):
    """Print current status of audio hardware and settings."""
    check_dependencies()
    current = get_current_devices()
    vol = get_volume_settings()
    outputs, inputs = get_available_devices()
    hw_info = get_hardware_info()

    print("=" * 64)
    print("            macOS Audio Settings - Current Status")
    print("=" * 64)
    print(f" Output Device : {current['output']}")
    print(f" Input Device  : {current['input']}")
    print(f" System Alerts : {current['system']}")
    print(f" Volume State  : {vol}")
    print("-" * 64)
    print(" Available Output Devices:")
    for d in outputs:
        marker = " [ACTIVE]" if d == current['output'] else ""
        srate = f" ({hw_info[d]['srate']} Hz)" if d in hw_info and hw_info[d]['srate'] else ""
        print(f"   • {d:<24}{srate}{marker}")
    print("\n Available Input Devices:")
    for d in inputs:
        marker = " [ACTIVE]" if d == current['input'] else ""
        srate = f" ({hw_info[d]['srate']} Hz)" if d in hw_info and hw_info[d]['srate'] else ""
        print(f"   • {d:<24}{srate}{marker}")
    print("=" * 64)

def cmd_apply_profile(profile_name):
    """Apply a predefined profile."""
    check_dependencies()
    if profile_name not in PROFILES:
        print(f"[x] Error: Unknown profile '{profile_name}'. Available: {', '.join(PROFILES.keys())}")
        sys.exit(1)

    prof = PROFILES[profile_name]
    print(f"[*] Applying Profile: {profile_name.upper()}")
    print(f"    Description: {prof['description']}")

    outputs, inputs = get_available_devices()

    # Output
    if prof["output"] in outputs:
        set_device(prof["output"], "output")
    else:
        print(f"  [!] Warning: Output '{prof['output']}' not detected.")

    # Input
    if prof["input"] in inputs:
        set_device(prof["input"], "input")
    else:
        print(f"  [!] Warning: Input '{prof['input']}' not detected.")

    # System alerts
    if prof["system"] in outputs:
        set_device(prof["system"], "system")

    # Input volume
    if "input_volume" in prof:
        set_input_volume(prof["input_volume"])

    print(f"[✓] Profile '{profile_name}' applied successfully!\n")

def cmd_test_output(args):
    """Play a test sound."""
    current = get_current_devices()
    duration = getattr(args, "duration", 5) if hasattr(args, "duration") else 5
    is_continuous = getattr(args, "continuous", False)

    if is_continuous:
        test_file = os.path.join(os.path.dirname(__file__), "assets", "test_tone_6s.wav")
        print(f"[*] Playing 6-second continuous test melody through: {current['output']} ...")
    else:
        test_file = "/System/Library/Sounds/Ping.aiff"
        if not os.path.exists(test_file):
            test_file = "/System/Library/Sounds/Tink.aiff"
        print(f"[*] Playing test chime (short 1.5s bell) through: {current['output']} ...")
        print("    (Note: This is a short chime. Use '--continuous' to play a 6-second melody).")

    res = subprocess.run(["afplay", test_file])
    if res.returncode == 0:
        print("[✓] Playback complete! Chime played successfully.")
    else:
        print("[x] Error: afplay failed.")

def cmd_test_device(device_name):
    """Temporarily route output to specific device and play continuous tone."""
    print(f"[*] Testing output on specific device: '{device_name}' ...")
    prev = get_current_devices()
    set_device(device_name, "output")
    test_file = os.path.join(os.path.dirname(__file__), "assets", "test_tone_6s.wav")
    if not os.path.exists(test_file):
        test_file = "/System/Library/Sounds/Ping.aiff"
    print(f"  [>] Playing 6-second test melody through {device_name}...")
    subprocess.run(["afplay", test_file])
    print(f"  [✓] Test completed on {device_name}.")


def cmd_test_input(args):
    """Record 2 seconds of audio and analyze volume level."""
    current = get_current_devices()
    print(f"[*] Testing microphone input from: {current['input']} ...")
    tmp_wav = "/tmp/audio_settings_input_test.wav"
    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        print("[!] ffmpeg not found in PATH.")
        print("[*] Install via: brew install ffmpeg")
        return

    print("  [>] Recording 2 seconds of audio into test buffer...")
    list_res = subprocess.run(
        [ffmpeg, "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    lines = list_res.stderr.splitlines()
    in_audio_section = False
    device_index = None

    for line in lines:
        if "AVFoundation audio devices:" in line:
            in_audio_section = True
            continue
        if in_audio_section:
            match = re.search(r"\[(\d+)\]\s+" + re.escape(current['input']), line)
            if match:
                device_index = f":{match.group(1)}"
                break

    if not device_index:
        device_index = ":default"

    cmd = [ffmpeg, "-y", "-f", "avfoundation", "-i", device_index, "-t", "2", tmp_wav]
    rec_res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if rec_res.returncode == 0 and os.path.exists(tmp_wav):
        size = os.path.getsize(tmp_wav)
        print(f"  [✓] Successfully recorded {size} bytes from {current['input']}.")
        vol_res = subprocess.run(
            [ffmpeg, "-i", tmp_wav, "-filter:a", "volumedetect", "-f", "null", "/dev/null"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        for vline in vol_res.stderr.splitlines():
            if "max_volume:" in vline or "mean_volume:" in vline:
                print(f"  [✓] {vline.strip()}")
        print("[✓] Microphone input verification PASSED!\n")
    else:
        print(f"[!] Recording test encountered an issue (Device index: {device_index}).")

def cmd_doctor(args):
    """Run comprehensive health checks and diagnostics."""
    print("=" * 64)
    print("                  Audio Doctor Diagnostics")
    print("=" * 64)

    # 1. SwitchAudioSource
    sw = shutil.which("SwitchAudioSource")
    print(f"[*] switchaudio-osx CLI : {'Installed (' + sw + ')' if sw else 'MISSING (brew install switchaudio-osx)'}")

    # 2. FFmpeg
    ff = shutil.which("ffmpeg")
    print(f"[*] ffmpeg CLI          : {'Installed (' + ff + ')' if ff else 'MISSING (brew install ffmpeg)'}")

    # 3. CoreAudio Daemon
    ps_res = run_cmd(["ps", "-A", "-o", "%cpu,pid,command"])
    core_lines = [l for l in (ps_res or "").splitlines() if "coreaudiod" in l]
    for line in core_lines:
        print(f"[*] CoreAudio daemon    : {line.strip()[:70]}")

    # 4. Hardware Devices & Sample Rates
    outputs, inputs = get_available_devices()
    hw_info = get_hardware_info()
    print("\n[*] Hardware Device Inventory:")
    hardware_targets = ["Scarlett 2i2 USB", "Elgato Wave:3", "Mac mini Speakers", "LG HDR 4K", "Wave Link Stream"]
    for hw in hardware_targets:
        found_out = "Output" if hw in outputs else ""
        found_in = "Input" if hw in inputs else ""
        roles = "/".join(filter(None, [found_out, found_in]))
        status_str = f"Detected ({roles})" if roles else "NOT DETECTED"
        srate_str = f" | {hw_info[hw]['srate']} Hz" if hw in hw_info and hw_info[hw].get("srate") else ""
        print(f"   • {hw:<20}: {status_str}{srate_str}")

    # 5. Routing Analysis
    current = get_current_devices()
    print("\n[*] Routing Configuration Health:")
    if current["output"] == "Mac mini Speakers":
        print("   [!] WARNING: Audio Output is set to internal Mac mini Speakers!")
        print("       Run './audio_settings.py fix' to switch to Scarlett 2i2 USB.")
    else:
        print(f"   [✓] Output routed to external interface: {current['output']}")

    if current["input"] == "Wave Link Stream":
        print("   [!] CAUTION: Audio Input is set to virtual 'Wave Link Stream' (96kHz).")
        print("       Ensure Wave Link app is open and unmuted, or run './audio_settings.py fix' for direct mic.")
    else:
        print(f"   [✓] Input routed to hardware microphone: {current['input']}")

    # 6. Sample Rate Mismatch Warning
    if "Wave Link Stream" in hw_info and "Scarlett 2i2 USB" in hw_info:
        wl_rate = hw_info["Wave Link Stream"].get("srate")
        sc_rate = hw_info["Scarlett 2i2 USB"].get("srate")
        if wl_rate and sc_rate and wl_rate != sc_rate:
            print(f"\n   [i] Notice: Sample rate difference detected:")
            print(f"       Scarlett 2i2 USB = {sc_rate} Hz vs Wave Link Stream = {wl_rate} Hz.")
            print(f"       In OBS/DAW video workflows, matching both to 48000 Hz in Audio MIDI Setup is recommended.")

    print("\n" + "=" * 64)

def cmd_restart_daemon(args):
    """Explain how to restart CoreAudio if frozen."""
    print("=" * 64)
    print("                 CoreAudio Daemon Restart")
    print("=" * 64)
    print("If audio freezes or USB interfaces become unresponsive, restart coreaudiod:")
    print("\n  Run command:")
    print("    sudo killall coreaudiod\n")
    print("macOS launchd will automatically relaunch coreaudiod cleanly within 2 seconds.")
    print("=" * 64)

def main():
    parser = argparse.ArgumentParser(description="macOS Audio Settings Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # status
    p_status = subparsers.add_parser("status", help="Show current audio device configuration")
    p_status.set_defaults(func=cmd_status)

    # doctor
    p_doctor = subparsers.add_parser("doctor", help="Run audio diagnostics and health check")
    p_doctor.set_defaults(func=cmd_doctor)

    # profile
    p_prof = subparsers.add_parser("profile", help="Apply an audio profile")
    p_prof.add_argument("name", choices=list(PROFILES.keys()), help="Profile name to apply")
    p_prof.set_defaults(func=lambda args: cmd_apply_profile(args.name))

    # fix / setup
    p_fix = subparsers.add_parser("fix", help="Automatically configure recommended video production settings")
    p_fix.set_defaults(func=lambda args: cmd_apply_profile("studio"))

    # test-output
    p_test_out = subparsers.add_parser("test-output", help="Play test sound on current output")
    p_test_out.add_argument("--continuous", action="store_true", help="Play 6-second continuous melody instead of 1.5s chime")
    p_test_out.set_defaults(func=cmd_test_output)

    # test-device
    p_test_dev = subparsers.add_parser("test-device", help="Test continuous audio on a specific device")
    p_test_dev.add_argument("name", help="Device name (e.g. 'Scarlett 2i2 USB', 'Elgato Wave:3', 'Mac mini Speakers', 'LG HDR 4K')")
    p_test_dev.set_defaults(func=lambda args: cmd_test_device(args.name))


    # test-input
    p_test_in = subparsers.add_parser("test-input", help="Record and verify microphone input")
    p_test_in.set_defaults(func=cmd_test_input)

    # set-output
    p_set_out = subparsers.add_parser("set-output", help="Manually set output device")
    p_set_out.add_argument("device", help="Device name")
    p_set_out.set_defaults(func=lambda args: set_device(args.device, "output"))

    # set-input
    p_set_in = subparsers.add_parser("set-input", help="Manually set input device")
    p_set_in.add_argument("device", help="Device name")
    p_set_in.set_defaults(func=lambda args: set_device(args.device, "input"))

    # restart-daemon
    p_restart = subparsers.add_parser("restart-daemon", help="Show instructions to restart CoreAudio")
    p_restart.set_defaults(func=cmd_restart_daemon)

    args = parser.parse_args()

    if not args.command:
        cmd_status(args)
    else:
        args.func(args)

if __name__ == "__main__":
    main()
