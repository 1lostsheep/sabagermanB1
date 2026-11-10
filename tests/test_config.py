from app import config


def test_env_parsing(tmp_path, monkeypatch):
    monkeypatch.delenv("PAZ_PIN", raising=False)
    f = tmp_path / ".env"
    f.write_text('PAZ_PIN=5678   # my pin\nLEARNER_NAME="Saba"\nPORT = 8765\n# comment\nX="a # b" # c\n', encoding="utf-8")
    v = config.load_env(f)
    assert v["PAZ_PIN"] == "5678"
    assert v["LEARNER_NAME"] == "Saba"
    assert v["PORT"] == "8765"
    assert v["X"] == "a # b"
