from pathlib import Path

root = Path(__file__).parent
text = (root / "docs/QUICKSTART_EVOLUTION.md").read_text()
assert "## Enviar texto com cURL" in text
assert "## Enviar mídia" in text
assert "## Python" in text
assert "## TypeScript" in text
assert "X-API-Key" in text
assert "X-Idempotency-Key" in text
assert "https://" in text
assert "EVOLUTION_API_KEY" in text
assert "mb_live_REDACTED" in text
for forbidden in ("sk-", "Bearer ey", "GLOBAL_API_KEY=", "instanceToken:"):
    assert forbidden not in text, forbidden
print("evolution quickstart validation passed")
