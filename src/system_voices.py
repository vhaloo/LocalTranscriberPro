"""Read installed operating-system voices and speak without network APIs."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess


def _windows_script(action):
    return ("[Console]::InputEncoding=[Text.Encoding]::UTF8; [Console]::OutputEncoding=[Text.Encoding]::UTF8; "
            "Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; " + action)


def installed_voices():
    system = platform.system()
    try:
        if system == "Windows":
            script = _windows_script("@($s.GetInstalledVoices() | Where-Object Enabled | ForEach-Object { "
                "@{id=$_.VoiceInfo.Name;language=$_.VoiceInfo.Culture.Name;name=$_.VoiceInfo.Name} }) | ConvertTo-Json -Compress")
            result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, encoding="utf-8-sig", timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            data = json.loads(result.stdout)
            return data if isinstance(data, list) else [data]
        if system == "Darwin" and shutil.which("say"):
            result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=10)
            voices = []
            for line in result.stdout.splitlines():
                head = line.split("#")[0].split()
                if len(head) >= 2:
                    voices.append({"id": " ".join(head[:-1]), "name": " ".join(head[:-1]), "language": head[-1]})
            return voices
        program = shutil.which("espeak-ng") or shutil.which("espeak")
        if system == "Linux" and program:
            result = subprocess.run([program, "--voices"], capture_output=True, text=True, timeout=10)
            return [{"id": parts[4], "name": parts[3], "language": parts[1]}
                    for line in result.stdout.splitlines()[1:] if len(parts := line.split()) >= 5]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return []


def speak_system(text, voice, slow, cancel_event):
    system = platform.system()
    if system == "Windows":
        script = _windows_script("$v=[Console]::In.ReadToEnd() | ConvertFrom-Json; "
                                 "$s.SelectVoice($v.voice); $s.Rate=$v.rate; $s.Speak($v.text); $s.Dispose()")
        command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
        payload = json.dumps({"text": text, "voice": voice, "rate": -2 if slow else 0}, ensure_ascii=False)
    elif system == "Darwin":
        command = ["say", "-v", voice, "-r", "145" if slow else "185"]
        payload = text
    else:
        command = [shutil.which("espeak-ng") or "espeak", "-v", voice, "-s", "140" if slow else "175", "--stdin"]
        payload = text
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if system == "Windows" else {}
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, text=True, encoding="utf-8", **options)
    try:
        process.stdin.write(payload)
        process.stdin.close()
        while process.poll() is None:
            if cancel_event.wait(0.1):
                process.terminate()
                break
        if not cancel_event.is_set() and process.wait(timeout=3) != 0:
            raise RuntimeError("The system voice could not speak this text")
    finally:
        if process.poll() is None:
            process.kill()
