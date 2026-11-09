import base64
import io
import wave

from tools import tts

VOICES = [
    {"name": "de-DE-Standard-A", "languageCodes": ["de-DE"], "ssmlGender": "FEMALE"},
    {"name": "de-DE-Neural2-C", "languageCodes": ["de-DE"], "ssmlGender": "FEMALE"},
    {"name": "de-DE-Chirp3-HD-Aoede", "languageCodes": ["de-DE"], "ssmlGender": "FEMALE"},
    {"name": "de-DE-Wavenet-B", "languageCodes": ["de-DE"], "ssmlGender": "MALE"},
    {"name": "de-DE-Neural2-D", "languageCodes": ["de-DE"], "ssmlGender": "MALE"},
    {"name": "de-AT-Neural2-A", "languageCodes": ["de-AT"], "ssmlGender": "MALE"},
]


def test_voice_type():
    assert tts.voice_type("de-DE-Chirp3-HD-Aoede") == "Chirp3-HD"
    assert tts.voice_type("de-DE-Neural2-C") == "Neural2"
    assert tts.voice_type("de-DE-Polyglot-1") == "other"


def test_pick_voice_prefers_most_natural_german():
    assert tts.pick_voice(VOICES, "FEMALE") == "de-DE-Chirp3-HD-Aoede"
    assert tts.pick_voice(VOICES, "MALE") == "de-DE-Neural2-D"   # not the Austrian one
    assert tts.pick_voice([], "MALE") is None


def test_synth_request():
    r = tts.synth_request("Hallo", "de-DE-Neural2-C", 0.9)
    assert r["voice"] == {"languageCode": "de-DE", "name": "de-DE-Neural2-C"}
    assert r["audioConfig"]["speakingRate"] == 0.9 and r["audioConfig"]["audioEncoding"] == "LINEAR16"
    assert "speakingRate" not in tts.synth_request("Hallo", "x", None)["audioConfig"]


def _wav_b64():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\0\0" * 2400)
    return base64.b64encode(buf.getvalue()).decode()


def test_google_engine_picks_voices_and_writes_wav(tmp_path, monkeypatch):
    calls = []

    def fake_call(self, method, path, body=None):
        calls.append((method, path, body))
        if path.startswith("voices"):
            return {"voices": VOICES}
        return {"audioContent": _wav_b64()}

    monkeypatch.setattr(tts.GoogleEngine, "_call", fake_call)
    e = tts.GoogleEngine(api_key="k")
    assert e.voices == {"f": "de-DE-Chirp3-HD-Aoede", "m": "de-DE-Neural2-D"}
    e.synth_wav("m", "Guten Tag", tmp_path / "a.wav")
    with wave.open(str(tmp_path / "a.wav")) as w:
        assert w.getframerate() == 24000
    assert calls[-1][2]["voice"]["name"] == "de-DE-Neural2-D"


def test_retry_without_speed_when_voice_rejects_it(tmp_path, monkeypatch):
    bodies = []

    def fake_call(self, method, path, body=None):
        bodies.append(body)
        if "speakingRate" in body["audioConfig"]:
            raise RuntimeError("Google TTS error 400: speaking_rate is not supported for this voice")
        return {"audioContent": _wav_b64()}

    monkeypatch.setattr(tts.GoogleEngine, "_call", fake_call)
    e = tts.GoogleEngine(voice_f="v1", voice_m="v2")
    e.synth_wav("f", "Hallo", tmp_path / "b.wav")
    assert len(bodies) == 2 and (tmp_path / "b.wav").exists()


def test_make_engine_reads_env(monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "google")
    monkeypatch.setenv("GOOGLE_TTS_VOICE_F", "vf")
    monkeypatch.setenv("GOOGLE_TTS_VOICE_M", "vm")
    monkeypatch.setenv("GOOGLE_TTS_RATE", "0.85")
    e = tts.make_engine()
    assert isinstance(e, tts.GoogleEngine) and e.voices == {"f": "vf", "m": "vm"} and e.rate == 0.85
