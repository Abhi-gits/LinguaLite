# LinguaLite

LinguaLite is a login-free multilingual translation and writing assistant. It runs inference locally through [Ollama](https://ollama.com) by default, with an optional, explicitly configured Gemini API provider. The frontend and backend can be deployed independently.

## Features

- English-to-Hindi and Hindi-to-English translation with automatic source detection
- Natural, Formal, Casual, and Literal translation styles
- Separate grammar correction, explanation, alternative translation, and transliteration tasks
- Up to three alternative translations with concise nuance notes
- Hindi transliteration between Devanagari and Latin using the configured model
- Browser-local history with revisit and delete; copy and download results
- Loading, empty, error, and success states
- Input validation for empty and overly long text
- Clear messaging when the configured AI provider is unavailable
- Optional Gemini API provider selected in backend configuration
- Responsive, accessible interface

## Architecture

```
lingualite/
  backend/                 FastAPI API
    app/
      main.py              App factory, CORS, error handlers
      config.py            Environment settings
      schemas.py           Pydantic task request and response models
      api/routes.py        POST /api/assist, legacy /api/translate, GET /api/health
      services/            Task-specific assistant services
      providers/           Provider interface + Ollama and Gemini implementations
    tests/                 pytest suite with mocked providers
  frontend/                React + Vite + Tailwind CSS
```

Ollama is the default local provider. Gemini can be selected explicitly with `TRANSLATION_PROVIDER=gemini` and a backend-only `GEMINI_API_KEY`. There is **no automatic fallback** between providers. Only English and Hindi translation are registered as supported. Other pairs are rejected; a model's general multilingual ability is not a quality guarantee.

User text is sent to the configured provider for the duration of a request. It is sent to Google when Gemini is selected. History is stored in browser localStorage and is only submitted to the provider when the user explicitly starts a new task.

## Prerequisites

- Node.js 20+
- Python 3.11+
- [Ollama](https://ollama.com/download) running locally for live translation
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/) only if using Gemini

## Installation and startup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API listens on `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The development server listens on `http://localhost:5173` and proxies `/api` to the backend.

For a production frontend build that talks to a separately hosted API:

```bash
cd frontend
VITE_API_BASE_URL=https://api.example.com npm run build
```

## Ollama model setup

LinguaLite defaults to **DeepSeek-R1** (`deepseek-r1:latest`), which is already installed in the local Ollama instance used for development. The available Ollama model is an 8.2B Qwen3-family build; model quality should be evaluated for your own English/Hindi translation use.

```bash
ollama serve
ollama list
```

Override the model with `OLLAMA_MODEL` in `backend/.env` if you prefer another installed multilingual model that you have evaluated for English and Hindi. If you change the model, make sure its exact tag appears in `ollama list`.

Confirm Ollama is reachable at `http://127.0.0.1:11434` before translating.

## Gemini API provider

Gemini is opt-in. Keep the API key in the backend environment; never put it in frontend code or a `VITE_` variable. In `backend/.env`, set:

```dotenv
TRANSLATION_PROVIDER=gemini
GEMINI_API_KEY=your-google-ai-studio-api-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=60
```

Restart the backend after changing environment settings. The health endpoint reports the selected provider. Gemini sends translation text to Google's API and is subject to Google's current model availability, rate limits, pricing, and data-use terms. Check the [Gemini API pricing and free-tier terms](https://ai.google.dev/gemini-api/docs/pricing) before use; free-tier access and quotas can vary. The app does not fall back to Ollama if Gemini is unavailable.

## Task API

### `POST /api/assist`

All requests require `task` and `text`. Task-specific fields:

| Task | Additional fields | Output |
| --- | --- | --- |
| `translate` | `source_language` (`en`, `hi`, `auto`), `target_language` (`en`, `hi`), `style` (`natural`, `formal`, `casual`, `literal`), optional `alternatives` (0–3), optional `include_explanation` | `translated_text`, optional structured alternatives and separate explanation |
| `grammar` | `source_language` (`en`, `hi`, `auto`) | `corrected_text`, concise `changes`; does not translate |
| `explain` | `source_language` (`en`, `hi`, `auto`) | concise `explanation`; original text is unchanged |
| `transliterate` | Hindi `source_language`, `source_script` (`auto`, `latin`, `devanagari`), `target_script` (`latin`, `devanagari`) | `transliterated_text`, separate from translation |

Example:

```json
{
  "task": "translate",
  "text": "Good morning",
  "source_language": "auto",
  "target_language": "hi",
  "style": "formal",
  "alternatives": 2,
  "include_explanation": true
}
```

Automatic language detection uses the selected provider and only accepts a language in the registry. It is model-assisted, not a separately benchmarked language-identification model. The legacy `POST /api/translate` remains available for clients using its `simple`/`advanced` modes.

## Legacy translation API

### `GET /api/health`

Liveness check. Does not call the model.

```json
{
  "status": "ok",
  "provider": "ollama",
  "model": "deepseek-r1:latest"
}
```

### `POST /api/translate`

Request:

```json
{
  "text": "Good morning",
  "source_language": "en",
  "target_language": "hi",
  "mode": "simple"
}
```

| Field | Notes |
| --- | --- |
| `text` | Required, 1–4000 characters after trimming |
| `source_language` | `en` or `hi` |
| `target_language` | `en` or `hi`, must differ from source |
| `mode` | `simple` or `advanced` |

Success response:

```json
{
  "translated_text": "सुप्रभात",
  "source_language": "en",
  "target_language": "hi",
  "mode": "simple",
  "provider": "ollama"
}
```

Error body (no stack traces):

```json
{
  "error": "model_unavailable",
  "message": "The AI model is unavailable. Start Ollama locally and pull the configured model."
}
```

| Status | `error` | When |
| --- | --- | --- |
| 422 | `invalid_request` | Empty text, unsupported language, same language pair, invalid mode, or text too long |
| 502 | `malformed_response` | Model output missing or unusable |
| 503 | `model_unavailable`, `provider_*` | Local model/provider unavailable, Gemini configuration issue, or Gemini quota/rate limit |
| 504 | `timeout` | Inference exceeded the selected provider's timeout |

## Testing

```bash
cd backend
source .venv/bin/activate
pytest
```

The suite validates request and task schemas, language pairs, styles, detection, task outputs, and API behavior with mocked providers. Ollama and Gemini HTTP responses are mocked for success, timeout, unavailability, and malformed output. Tests never treat hardcoded sample translations as live model results.

## Privacy and limitations

- LinguaLite's backend does not persist requests or results; the browser can store submitted results in localStorage history.
- History is stored in this browser only; clearing browser site data removes it. A history entry is sent to a provider only when explicitly submitted again as a new task.
- Transliteration is model-generated colloquial romanization, not deterministic standards-based transliteration. Verify names and pronunciation-sensitive text.
- By default, text is sent only to the local Ollama process. When Gemini is explicitly selected, translation text is sent to Google's API. Review Google's [Gemini API terms](https://ai.google.dev/gemini-api/terms) and current [pricing/data-use details](https://ai.google.dev/gemini-api/docs/pricing) before sending sensitive text.
- Output is generated by an AI model and can be inaccurate, incomplete, or biased.
- The application will not invent a translation when inference fails.
- English ↔ Hindi is the only registered translation pair. Add languages only after evaluating the configured model and testing the specific pairs.

## Deployment

Frontend and backend can be deployed independently.

**Backend:** run `uvicorn app.main:app --host 0.0.0.0 --port 8000` behind a reverse proxy. Set `CORS_ORIGINS` to the frontend origin(s). Point `OLLAMA_BASE_URL` at a reachable Ollama instance. Do not expose Ollama publicly unless you intend to.

**Frontend:** `npm run build` and serve `frontend/dist`. Set `VITE_API_BASE_URL` to the public API origin at build time.

Keep Ollama on a private network or the same host as the API. For Gemini deployments, store `GEMINI_API_KEY` in the backend platform's secret manager.

## Model licensing notes

The default DeepSeek-R1 model weights are distributed under the [MIT License](https://ollama.com/library/deepseek-r1). Review the model and runtime license terms (and the license of any replacement model) before redistribution or commercial use. LinguaLite itself does not redistribute model weights.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins |
| `MAX_TEXT_LENGTH` | `4000` | Server-side input cap; may be lowered to any value from 1 to 4000 |
| `TRANSLATION_PROVIDER` | `ollama` | `ollama` (local) or explicitly selected `gemini` |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama endpoint |
| `OLLAMA_MODEL` | `deepseek-r1:latest` | Installed local Ollama model tag |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Inference timeout |
| `GEMINI_API_KEY` | empty | Backend-only Google AI Studio API key; required only for Gemini |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini API model id |
| `GEMINI_TIMEOUT_SECONDS` | `60` | Gemini request timeout |
| `VITE_API_BASE_URL` | empty (same-origin `/api`) | Frontend API origin for independent deploys |
