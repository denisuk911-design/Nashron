from __future__ import annotations

import math
import struct
import time
import wave
from pathlib import Path
from typing import Callable


class ChatSoundService:
    """Creates and plays small original notification tones on Windows."""

    def __init__(
        self,
        sound_dir: Path,
        settings: dict[str, object],
        *,
        player: Callable[[Path], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.sound_dir = sound_dir
        self._player = player or self._play_windows
        self._clock = clock
        self._last_receive_at = -10.0
        self.configure(settings)

    def configure(self, settings: dict[str, object]) -> None:
        self.enabled = bool(settings.get("message_sounds_enabled", True))
        self.send_enabled = bool(settings.get("send_sound_enabled", True))
        self.receive_enabled = bool(settings.get("receive_sound_enabled", True))
        try:
            volume = int(settings.get("message_sound_volume", 35))
        except (TypeError, ValueError):
            volume = 35
        self.volume = max(0, min(100, volume))

    def play_send(self) -> bool:
        if not self.enabled or not self.send_enabled or self.volume <= 0:
            return False
        return self._play("send")

    def play_receive(self) -> bool:
        if not self.enabled or not self.receive_enabled or self.volume <= 0:
            return False
        now = self._clock()
        if now - self._last_receive_at < 0.45:
            return False
        played = self._play("receive")
        if played:
            self._last_receive_at = now
        return played

    def _play(self, kind: str) -> bool:
        try:
            path = self._ensure_wave(kind)
            self._player(path)
        except (OSError, ValueError, wave.Error):
            return False
        return True

    def _ensure_wave(self, kind: str) -> Path:
        if kind not in {"send", "receive"}:
            raise ValueError("unsupported_chat_sound")
        self.sound_dir.mkdir(parents=True, exist_ok=True)
        path = self.sound_dir / f"team2050-{kind}-{self.volume}.wav"
        if path.exists():
            return path

        sample_rate = 22050
        duration = 0.13 if kind == "send" else 0.19
        frames: list[bytes] = []
        for index in range(int(sample_rate * duration)):
            position = index / sample_rate
            progress = position / duration
            attack = min(1.0, position / 0.012)
            release = max(0.0, 1.0 - progress) ** 2
            if kind == "send":
                frequency = 520.0 + 390.0 * progress
                signal = math.sin(2.0 * math.pi * frequency * position)
            else:
                signal = (
                    math.sin(2.0 * math.pi * 660.0 * position)
                    + 0.55 * math.sin(2.0 * math.pi * 990.0 * position)
                ) / 1.55
            amplitude = 0.22 * (self.volume / 100.0) * attack * release
            frames.append(struct.pack("<h", int(32767 * amplitude * signal)))

        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(b"".join(frames))
        return path

    @staticmethod
    def _play_windows(path: Path) -> None:
        import winsound

        winsound.PlaySound(
            str(path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
