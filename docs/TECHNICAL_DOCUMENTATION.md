# LinguaLite Technical Documentation

## 1. Project overview

LinguaLite is a browser-based translation and writing assistant with a React/Vite frontend and a FastAPI backend. The backend can use a local Ollama model by default or an explicitly selected Gemini API provider. The frontend and backend are independently runnable and deployable.

The language registry contains English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, and Punjabi. Every distinct source/target combination is enabled. The eight additional regional languages are marked **early access** and are not independently quality-validated; enabling a pair is not a claim that the configured model has been benchmarked for it. Automatic source detection asks the selected model to identify the input language and accepts only a code in the registry.

## 2. Feature status and boundaries

| Feature | Current behavior | Important limitation |
| --- | --- | --- |
| Translate | Any pair in the ten-language registry, source can be `auto`; style is Natural, Formal, Casual, or Literal | The eight new regional languages are early access; detection and translation are not independently benchmarked for them |
| India Connect | Drafts a target-language message from a described intent, with audience choice, approximate Latin-letter pronunciation, and a tone note | Model-generated aid; audience is a formality cue, not a guarantee of cultural appropriateness |
| Grammar | Corrects spelling and grammar in a selected/detected registered language without a translation task | New regional languages are early access; output may change intended nuance |
| Explain | Produces a concise explanation in the selected/detected registered language | Explanations are AI-generated, not authoritative linguistic annotation |
| Alternatives | Requests 1–3 alternatives and short nuance labels; exact normalized duplicates of the primary/other variants are removed | Semantic equivalence is instructed, not programmatically proven |
| Transliterate | Model-generated Hindi conversion between Devanagari and Latin scripts | Colloquial and model-dependent; not deterministic standards-based transliteration |
| History/export | Browser localStorage stores up to 50 successful results; users can revisit/delete entries, copy output, or download primary output as text | Storage is browser-local, may be removed by browser data clearing, and is not encrypted by the app |

No task silently overwrites the source. A task must be submitted explicitly. History records are not sent to the provider merely by viewing them; a user must submit a task again to generate new output.

## 3. Architecture

```text
Browser
  React components
  ├── Task/style/language controls
  ├── Result, alternatives, explanation
  └── localStorage history
        │ POST /api/assist
        ▼
FastAPI application
  ├── Pydantic request and response validation
  ├── WritingAssistantService dispatch
  ├── Task-specific services
  └── TranslationProvider interface
        ├── OllamaProvider (default/local)
        └── GeminiProvider (explicit opt-in/cloud)
```

### Backend modules

- `backend/app/main.py`: application factory, lifespan, HTTP client, CORS, and error handlers.
- `backend/app/config.py`: environment-based settings.
- `backend/app/constants.py`: maximum request length, language names, supported pairs, and legacy mode values.
- `backend/app/schemas.py`: Pydantic request and response contracts.
- `backend/app/api/routes.py`: health, task API, and backward-compatible translation endpoint.
- `backend/app/providers/base.py`: provider interface (`generate` and legacy `translate`).
- `backend/app/providers/ollama.py`: Ollama generate endpoint adapter.
- `backend/app/providers/gemini.py`: Gemini `generateContent` endpoint adapter.
- `backend/app/providers/prompts.py`: shared translation style prompts and output cleanup.
- `backend/app/services/assistant.py`: task dispatch and response assembly.
- `backend/app/services/translation.py`: detection, supported-pair checks, translation.
- `backend/app/services/india_connect.py`: intent-based message draft, pronunciation aid, and audience-aware tone note.
- `backend/app/services/grammar.py`: same-language grammar correction.
- `backend/app/services/explanation.py`: separate explanation generation.
- `backend/app/services/alternatives.py`: alternatives and duplicate filtering.
- `backend/app/services/transliteration.py`: model-instructed Hindi script conversion.
- `backend/app/services/structured.py`: JSON parsing and Pydantic validation for model-generated task results.

### Frontend modules

- `frontend/src/components/Translator.jsx`: task form, result rendering, local history, copy, and download controls.
- `frontend/src/api.js`: API request and normalized error handling.
- `frontend/src/constants.js`: languages, task names, styles, and frontend request limit.
- `frontend/src/components/Header.jsx` and `Footer.jsx`: application identity and privacy notice.
- `frontend/vite.config.js`: development proxy from `/api` to `http://127.0.0.1:8000`.

## 4. Request lifecycle

1. The browser validates that the user has entered text and shows its character count.
2. It submits a task-specific JSON request to `POST /api/assist`.
3. FastAPI validates task fields, source/target languages, styles, scripts, alternative count, and text.
4. `WritingAssistantService` dispatches to the relevant service.
5. If source is `auto`, the translation service asks the selected provider for one supported language code. Unknown or unsupported detections stop the request.
6. The provider sends an asynchronous HTTP request to Ollama or Gemini, using its configured timeout.
7. Structured task output is parsed and validated before being returned. Missing/invalid content raises an API error; the backend does not construct a fake success result.
8. On success, the browser renders the response and saves a copy to localStorage.

The backend does not intentionally log user text. Do not enable HTTP body logging at a proxy or observability layer without reviewing its privacy impact.

## 5. API reference

### `GET /api/health`

Returns configured provider and model. This is a liveness/configuration response; it does not test model credentials, contact Ollama/Gemini, or prove inference availability.

```json
{
  "status": "ok",
  "provider": "ollama",
  "model": "deepseek-r1:latest"
}
```

### `POST /api/assist`

All tasks require `task` and non-blank `text`. The maximum is 4,000 characters by default. `MAX_TEXT_LENGTH` may lower, but not raise, that ceiling.

#### Translate

Request:

```json
{
  "task": "translate",
  "text": "Good morning",
  "source_language": "auto",
  "target_language": "hi",
  "style": "natural",
  "alternatives": 2,
  "include_explanation": true
}
```

- `source_language`: `en`, `hi`, `ta`, `te`, `kn`, `ml`, `bn`, `mr`, `gu`, `pa`, or `auto`; defaults to `auto`.
- `target_language`: required; one of the ten listed languages.
- `style`: `natural`, `formal`, `casual`, or `literal`; defaults to `natural`.
- `alternatives`: integer 0–3; defaults to 0.
- `include_explanation`: boolean; defaults to false.

Response fields include `translated_text`, resolved `source_language`, `target_language`, `style`, `provider`, `alternatives` (each with `text` and `nuance`), and optional separate `explanation`.
Responses include `early_access: true` whenever either language is one of the eight additional regional languages.

#### India Connect

Creates a practical message from a stated intent rather than requiring the user to compose a finished sentence. The selected audience influences formality only; the prompt forbids inventing details or treating cultural guidance as universal.

```json
{
  "task": "india_connect",
  "text": "Ask where the nearest bus stop is.",
  "source_language": "en",
  "target_language": "ta",
  "audience": "service_staff"
}
```

`audience` is one of `general`, `friend`, `elder`, `professional`, or `service_staff`. The response contains `translated_text`, `pronunciation_help` (approximate Latin-letter rendering), `tone_guidance`, and `early_access`. The message card's copy/download controls include all three text fields.

#### Grammar

```json
{
  "task": "grammar",
  "text": "I is going to the store.",
  "source_language": "en"
}
```

Response includes `corrected_text`, `changes`, and the resolved source language. The service instructs the model to preserve language and avoid translation.

#### Explain

```json
{
  "task": "explain",
  "text": "Break the ice.",
  "source_language": "en"
}
```

Response contains `explanation` separately; it does not replace or alter the source text.

#### Transliterate

```json
{
  "task": "transliterate",
  "text": "नमस्ते",
  "source_language": "hi",
  "source_script": "devanagari",
  "target_script": "latin"
}
```

`source_script` is `auto`, `latin`, or `devanagari`; `target_script` is `latin` or `devanagari`. Both scripts cannot be identical when source script is explicitly supplied. This separate task remains restricted to Hindi; India Connect provides approximate Latin-letter pronunciation aids for the other target languages.

### Legacy `POST /api/translate`

Kept for compatibility with earlier frontend/API clients. It accepts `text`, any registered `source_language` and `target_language`, and `mode` (`simple` or `advanced`), and returns `translated_text`, language codes, mode, provider, and `early_access`. New clients should use `/api/assist`.

### Error responses

Errors use the shape `{"error":"…","message":"…"}`. Common status codes:

| Status | Meaning |
| --- | --- |
| 422 | Invalid request, unsupported language/pair, invalid task parameters, or text over limit |
| 502 | Provider returned malformed/unusable model output |
| 503 | Provider unavailable, not configured, invalid credentials, or rate/quota-limited |
| 504 | Provider inference timed out |

Internal stack traces and provider response bodies are not returned to the caller.

## 6. Configuration

Backend settings are read from environment variables or `backend/.env`. Start from `backend/.env.example`.

| Variable | Default | Notes |
| --- | --- | --- |
| `TRANSLATION_PROVIDER` | `ollama` | `ollama` or explicitly selected `gemini`; no fallback |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama host accessible from the backend |
| `OLLAMA_MODEL` | `deepseek-r1:latest` | Must exist in Ollama; test language quality yourself |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Ollama request timeout |
| `GEMINI_API_KEY` | empty | Backend-only secret; never put in frontend or a `VITE_` variable |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Must be available to the key/project and support `generateContent` |
| `GEMINI_TIMEOUT_SECONDS` | `60` | Gemini request timeout |
| `MAX_TEXT_LENGTH` | `4000` | Configurable 1–4,000 characters |
| `CORS_ORIGINS` | local Vite origins | Comma-separated allowed browser origins |
| `VITE_API_BASE_URL` | empty | Optional frontend build-time API origin |

## 7. Local development

### Backend

```bash
cd backend
python3 -m venv .venv        # only if the environment is absent
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API base is `http://127.0.0.1:8000`; interactive API docs are at `/docs`. The API does not serve the React homepage at `/`.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. Vite proxies API calls to port 8000. For Gemini, set `TRANSLATION_PROVIDER=gemini` and a valid `GEMINI_API_KEY` in `backend/.env`, then restart the backend.

### Ollama

Install Ollama, start it, and pull a model. LinguaLite's default tag is `deepseek-r1:latest`; if absent, pull that tag or configure `OLLAMA_MODEL` to an installed compatible model. Model size affects speed and memory. Verify behavior for each language pair you plan to use; the eight additional regional languages remain early access.

## 8. Tests and checks

From the repository root:

```bash
backend/.venv/bin/python -m pytest backend/tests -q
cd frontend
npm run lint
npm run build
```

Backend tests mock model HTTP responses and cover schema validation, provider behavior, error cases, auto-detection, style prompts, each task, malformed structured outputs, and API response shapes. They do not measure live model quality.

## 9. Deployment

- Deploy the backend and frontend independently.
- Run the FastAPI app behind a production ASGI server and reverse proxy.
- Set `CORS_ORIGINS` to the deployed frontend origin(s).
- Set model/provider environment variables in the backend deployment environment.
- Keep Ollama private and accessible only to the backend. Do not expose the Ollama port publicly without a specific security plan.
- For Gemini, store `GEMINI_API_KEY` in the hosting platform's secret manager.
- Build the frontend with `VITE_API_BASE_URL` set when the API is not same-origin.
- Serve the frontend `dist/` output over HTTPS.

## 10. Privacy, security, and model limitations

- Ollama mode sends input to the configured Ollama host; it is local only if that host is local/trusted.
- Gemini mode sends task text to Google's API. Review current Gemini API pricing, quota, data-use, and retention terms before using sensitive content.
- The backend does not store history. Browser history resides in localStorage and can be cleared by the user through browser site-data controls.
- Model output can be wrong, incomplete, biased, or unsafe to rely on in high-stakes settings. Review important results.
- The eight additional regional languages are enabled as early access but have not been independently quality-validated. API responses mark these requests with `early_access: true`; verify meaning, names, amounts, tone, and pronunciation with a fluent speaker.
- Avoid logging API keys, request bodies, or complete user texts. Use secret management and HTTPS for hosted deployments.

## 11. Research scope

This section proposes research work; it does not claim that an evaluation has been completed.

### Research questions

1. How accurate and meaning-preserving are translations for each language pair among English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, and Punjabi?
2. How often does model-assisted detection identify each language correctly, especially for short, mixed-language, or ambiguous input?
3. Does India Connect preserve a user's stated intent and details, and do audience choices improve message suitability without introducing cultural stereotypes?
4. Are its Latin-letter pronunciation aids understandable to readers and faithful enough to help with speaking?
5. Do Natural, Formal, Casual, and Literal styles create reliably distinguishable register changes without changing factual meaning?
6. Do grammar corrections, explanations, and alternatives remain useful and faithful across scripts and languages?
7. What are the latency, memory, privacy, and cost trade-offs between local Ollama models and explicitly configured hosted inference?

### Suggested methodology

- Create a consented, anonymized evaluation set for each language and direction, including regional-to-regional pairs, with balanced text categories and documented references. Do not use private production inputs without explicit consent and governance.
- Use reviewers fluent in each language pair for adequacy, fluency, terminology, tone, and meaning preservation; blind reviewers to model/provider where practical.
- Measure task-specific outcomes: translation adequacy/fluency; detection accuracy and abstention by script; India Connect intent/detail retention and audience suitability; pronunciation-aid usefulness; grammar precision; explanation faithfulness; alternative diversity and semantic equivalence.
- Record provider/model version, quantization, hardware, prompt/style, input size, latency, failures, and configuration. Do not publish API keys or personal text.
- Report sample selection, reviewer instructions, disagreements, limitations, and confidence intervals. Automated metrics may supplement, but should not replace, bilingual human review.
- Benchmark local and hosted routes separately and document the provider's applicable data-use terms. Do not describe a model as “tested” unless the tested version, languages, dataset, and evaluation are reported.

### Out of scope until separately approved

- Claiming validated quality for an early-access language or pair before evaluation.
- High-stakes legal, medical, immigration, or official certified translation.
- User accounts, server-side translation history, collaboration, or cloud synchronization.
- Training or fine-tuning models on user content.
- Claims of deterministic transliteration from the current AI transliteration path.
