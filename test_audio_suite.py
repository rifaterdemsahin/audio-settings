#!/usr/bin/env python3
"""
Comprehensive Audio Test Suite and Diagnostic Probe for Mac mini.
Tests all output devices, input devices, sample rates, drivers, and latency.
"""

import subprocess
import time
import json
import os
import sys

OUTPUT_FILE = "diagnostics_data.json"

def run_cmd(cmd, timeout=30):
    try:
        start = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        duration = time.time() - start
        return {
            "success": res.returncode == 0,
            "returncode": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "elapsed_sec": round(duration, 3)
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "timeout": True, "elapsed_sec": timeout}
    except Exception as e:
        return {"success": False, "error": str(e), "elapsed_sec": 0}

def main():
    report = {}

    print("=== STEP 1: Probing Audio Devices and Sample Rates ===")
    sp_res = run_cmd(["system_profiler", "SPAudioDataType", "-json"], timeout=45)
    devices = []
    if sp_res["success"] and sp_res["stdout"]:
        try:
            raw = json.loads(sp_res["stdout"])
            for g in raw.get("SPAudioDataType", []):
                for item in g.get("_items", []):
                    devices.append({
                        "name": item.get("_name"),
                        "manufacturer": item.get("coreaudio_device_manufacturer"),
                        "sample_rate": item.get("coreaudio_device_srate"),
                        "transport": item.get("coreaudio_device_transport"),
                        "input_channels": item.get("coreaudio_device_input", 0),
                        "output_channels": item.get("coreaudio_device_output", 0),
                        "is_default_output": item.get("coreaudio_default_audio_output_device") == "spaudio_yes",
                        "is_default_input": item.get("coreaudio_default_audio_input_device") == "spaudio_yes",
                        "is_default_system": item.get("coreaudio_default_audio_system_device") == "spaudio_yes"
                    })
        except Exception as e:
            report["sp_error"] = str(e)
    report["devices"] = devices
    print(f"Detected {len(devices)} audio devices.")

    print("\n=== STEP 2: Inspecting Audio HAL Plugins ===")
    hal_res = run_cmd(["ls", "-la", "/Library/Audio/Plug-Ins/HAL"])
    report["hal_plugins"] = hal_res["stdout"]

    print("\n=== STEP 3: Checking Running Audio Daemons & Processes ===")
    ps_res = run_cmd(["ps", "-A", "-o", "pid,%cpu,time,comm"])
    audio_procs = [l.strip() for l in ps_res["stdout"].splitlines() if any(k in l.lower() for k in ["audio", "wave", "scarlett", "focusrite"])]
    report["audio_processes"] = audio_procs

    print("\n=== STEP 4: Testing Output Playback on Available Devices ===")
    output_targets = ["Scarlett 2i2 USB", "Elgato Wave:3", "Mac mini Speakers", "LG HDR 4K"]
    output_tests = {}
    test_tone = os.path.abspath("assets/test_tone_6s.wav")

    for dev in output_targets:
        matching = [d for d in devices if d["name"] == dev and d["output_channels"] > 0]
        if not matching:
            output_tests[dev] = {"status": "DEVICE_NOT_FOUND"}
            continue

        print(f"[*] Testing output playback on: {dev} ...")
        # Set output
        sw_res = run_cmd(["SwitchAudioSource", "-s", dev, "-t", "output"], timeout=15)
        # Play short chime (1s) to test startIO
        t_start = time.time()
        play_res = run_cmd(["afplay", test_tone], timeout=20)
        output_tests[dev] = {
            "switch_result": sw_res,
            "play_result": play_res,
            "total_latency_sec": round(time.time() - t_start, 3),
            "status": "SUCCESS" if play_res["success"] else "FAILED"
        }
        print(f"    -> {dev}: Status = {output_tests[dev]['status']}, Latency = {output_tests[dev]['total_latency_sec']}s")

    report["output_tests"] = output_tests

    print("\n=== STEP 5: Testing Input Recording on Microphones ===")
    input_targets = ["Elgato Wave:3", "Scarlett 2i2 USB"]
    input_tests = {}
    
    # Get avfoundation audio device indices
    av_res = run_cmd(["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""], timeout=60)
    av_stderr = av_res.get("stderr", "")
    
    for dev in input_targets:
        print(f"[*] Testing input recording on: {dev} ...")
        # Search index in avfoundation list
        import re
        match = re.search(r"\[(\d+)\]\s+" + re.escape(dev), av_stderr)
        dev_idx = f":{match.group(1)}" if match else ":default"
        
        # Switch input
        sw_in = run_cmd(["SwitchAudioSource", "-s", dev, "-t", "input"], timeout=15)
        
        # Record 1.5 seconds
        tmp_rec = f"/tmp/diag_test_{dev.replace(' ', '_')}.wav"
        rec_res = run_cmd(["ffmpeg", "-y", "-f", "avfoundation", "-i", dev_idx, "-t", "1.5", tmp_rec], timeout=15)
        
        vol_info = {}
        if rec_res["success"] and os.path.exists(tmp_rec):
            size = os.path.getsize(tmp_rec)
            vol_res = run_cmd(["ffmpeg", "-i", tmp_rec, "-filter:a", "volumedetect", "-f", "null", "/dev/null"], timeout=10)
            for vl in vol_res.get("stderr", "").splitlines():
                if "max_volume:" in vl or "mean_volume:" in vl:
                    vol_info[vl.split(":")[0].strip()] = vl.strip()
            input_tests[dev] = {
                "status": "RECORDING_SUCCESS",
                "bytes": size,
                "volume": vol_info,
                "device_index": dev_idx,
                "elapsed_sec": rec_res["elapsed_sec"]
            }
        else:
            input_tests[dev] = {
                "status": "RECORDING_FAILED",
                "device_index": dev_idx,
                "rec_res": rec_res
            }
        print(f"    -> {dev}: Status = {input_tests[dev]['status']}")

    report["input_tests"] = input_tests

    # Restore recommended profile: output = Scarlett 2i2 USB, input = Elgato Wave:3
    print("\n=== STEP 6: Restoring Standard Studio Profile ===")
    run_cmd(["SwitchAudioSource", "-s", "Scarlett 2i2 USB", "-t", "output"])
    run_cmd(["SwitchAudioSource", "-s", "Elgato Wave:3", "-t", "input"])
    run_cmd(["SwitchAudioSource", "-s", "Scarlett 2i2 USB", "-t", "system"])
    run_cmd(["osascript", "-e", "set volume input volume 85"])

    with open(OUTPUT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[✓] Diagnostics test completed! Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
