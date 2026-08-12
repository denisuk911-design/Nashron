import wave

from core.chat_sound_service import ChatSoundService


def test_chat_sounds_are_original_waves_and_receive_is_debounced(tmp_path):
    played = []
    now = [10.0]
    service = ChatSoundService(
        tmp_path,
        {
            "message_sounds_enabled": True,
            "send_sound_enabled": True,
            "receive_sound_enabled": True,
            "message_sound_volume": 40,
        },
        player=played.append,
        clock=lambda: now[0],
    )

    assert service.play_send() is True
    assert service.play_receive() is True
    assert service.play_receive() is False
    now[0] += 0.5
    assert service.play_receive() is True
    assert len(played) == 3

    for path in set(played):
        with wave.open(str(path), "rb") as sound:
            assert sound.getnchannels() == 1
            assert sound.getframerate() == 22050
            assert sound.getnframes() > 2000


def test_chat_sounds_respect_master_and_per_direction_switches(tmp_path):
    played = []
    service = ChatSoundService(
        tmp_path,
        {
            "message_sounds_enabled": False,
            "send_sound_enabled": True,
            "receive_sound_enabled": True,
            "message_sound_volume": 35,
        },
        player=played.append,
    )

    assert service.play_send() is False
    assert service.play_receive() is False
    service.configure(
        {
            "message_sounds_enabled": True,
            "send_sound_enabled": False,
            "receive_sound_enabled": True,
            "message_sound_volume": 0,
        }
    )
    assert service.play_send() is False
    assert service.play_receive() is False
    assert played == []
