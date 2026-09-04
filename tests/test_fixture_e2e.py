import json
import socket
import subprocess
import time
from pathlib import Path

from scripts.inspect_recording import inspect_recording


ROOT = Path(__file__).parents[1]
TEMPLATE = ROOT / "assets" / "playwright-demo-template"
FIXTURE = Path(__file__).parent / "fixture-app"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_local_fixture_rehearsal_recording_and_inspection(tmp_path: Path):
    audio = tmp_path / "master.wav"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=1.5", str(audio),
    ], check=True)
    manifest = tmp_path / "production.json"
    manifest.write_text(json.dumps({
        "title": "Fixture",
        "locale": "en-US",
        "voice": {"provider": "supplied", "model": "supplied", "voice_id": "fixture", "language": "en"},
        "chapters": [{
            "id": "01-flow", "narration": "Create and complete a profile.",
            "audio_path": audio.name, "duration_seconds": 1.5,
            "cues": [
                {"id": "enter-name", "at_seconds": 0.2, "action": "Enter a display name"},
                {"id": "continue", "at_seconds": 0.7, "action": "Continue"}
            ]
        }],
        "master_audio_path": audio.name,
        "chapter_gap_seconds": 0.25
    }), encoding="utf-8")
    timing = tmp_path / "master.wav.timing.json"
    timing.write_text(json.dumps({
        "duration_seconds": 1.5,
        "chapters": [{"id": "01-flow", "offset_seconds": 0, "duration_seconds": 1.5, "cues": [
            {"id": "enter-name", "master_at_seconds": 0.2},
            {"id": "continue", "master_at_seconds": 0.7}
        ]}]
    }), encoding="utf-8")
    port = free_port()
    server = subprocess.Popen(
        ["python", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=FIXTURE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.2)
        common = ["--manifest", str(manifest), "--app-url", f"http://127.0.0.1:{port}", "--output", str(tmp_path / "recording")]
        subprocess.run(["bun", "run", "record.ts", "--fast", *common], cwd=TEMPLATE, check=True, capture_output=True, text=True)
        subprocess.run(["bun", "run", "record.ts", *common], cwd=TEMPLATE, check=True, capture_output=True, text=True)
    finally:
        server.terminate()
        server.wait(timeout=5)
    recording = tmp_path / "recording" / "narrated-demo.mp4"
    report = inspect_recording(recording, timing, output_dir=tmp_path / "review")
    assert report["passed"] is True
