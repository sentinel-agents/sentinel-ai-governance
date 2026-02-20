# Sentinel

Minimal FastAPI-powered AI governance layer demonstrating multi-agent oversight with dual-mode intelligence (deterministic + OpenAI) and Filecoin/IPFS anchoring.

## Local Development

```powershell
cd sentinel
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/ to access the UI.

### Storage (Pinata/IPFS)

Set your Pinata JWT before running the server:

```powershell
$env:PINATA_JWT="YOUR_PINATA_JWT"
```

Every uploaded governance record is public once addressed by its CID. Never upload sensitive or secret data.

### LLM Configuration

Sentinel can operate in two modes:

- **MOCK** – deterministic engine (default when no OpenAI key is present)
- **OPENAI** – delegates agent scoring to an OpenAI model

Environment variables:

```powershell
$env:OPENAI_API_KEY="sk-..."           # optional; enables OPENAI mode
$env:SENTINEL_MODE="openai"            # force OpenAI (requires API key)
$env:SENTINEL_MODE="mock"              # force deterministic mock
$env:SENTINEL_MODE="auto"              # default; use OpenAI only if key present
```

If OpenAI is requested but unavailable (missing key, HTTP errors, parse issues), Sentinel automatically falls back to the deterministic engine, adds `llm_fallback_mock` (and `llm_parse_error` when parsing fails), and the UI displays a warning banner.

### Sample run indicators

- **Mode: OPENAI** – live LLM outputs in use
- **Mode: AUTO->MOCK** – auto mode fell back to deterministic engine (no key found)
- **Mode: OPENAI->MOCK** – OpenAI was requested but failed; fallback engaged (see conflict flags)

### Hash semantics

- `sha256` (pre-upload) covers the canonical JSON payload with an empty CID — exactly what is pushed to Pinata/IPFS.
- `sha256_post` hashes the final record after the CID is embedded in the storage reference.

Both hashes use canonical serialization (`json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`).
