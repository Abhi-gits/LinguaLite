# LinguaLite Technical Documentation

## 1. Project overview

LinguaLite is a browser-based translation and writing assistant with a React/Vite frontend and a FastAPI backend. The backend can use a local Ollama model by default or an explicitly selected Gemini API provider. The frontend and backend are independently runnable and deployable.

Current supported translation pair: **English ↔ Hindi**. Other language pairs are rejected until they are deliberately added and evaluated. Automatic source detection asks the selected model to identify the input language and accepts only a code in the application registry.

## 2. Feature status and boundaries

| Feature | Current behavior | Important limitation |
| --- | --- | --- |
| Translate | English/Hindi, source can be `auto`, target is selected; style is Natural, Formal, Casual, or Literal | Detection uses the configured generative model; it is not a separately benchmarked language detector |
| Grammar | Corrects spelling and grammar in English or Hindi without a translation task | Model output may still change intended nuance; users should review it before using |
| Explain | Produces a concise explanation in the selected/detected input language | Explanations are AI-generated, not authoritative linguistic annotation |
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

- `source_language`: `en`, `hi`, or `auto`; defaults to `auto`.
- `target_language`: required, `en` or `hi`.
- `style`: `natural`, `formal`, `casual`, or `literal`; defaults to `natural`.
- `alternatives`: integer 0–3; defaults to 0.
- `include_explanation`: boolean; defaults to false.

Response fields include `translated_text`, resolved `source_language`, `target_language`, `style`, `provider`, `alternatives` (each with `text` and `nuance`), and optional separate `explanation`.

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

`source_script` is `auto`, `latin`, or `devanagari`; `target_script` is `latin` or `devanagari`. Both scripts cannot be identical when source script is explicitly supplied. The task is restricted to Hindi.

### Legacy `POST /api/translate`

Kept for compatibility with earlier frontend/API clients. It accepts `text`, `source_language`, `target_language`, and `mode` (`simple` or `advanced`) and returns `translated_text`, language codes, mode, and provider. New clients should use `/api/assist`.

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
| `GEMINI_MODEL` | `gemini-2.5-flash` | Must be available to the key/project |
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

Install Ollama, start it, and pull a model. LinguaLite's default tag is `deepseek-r1:latest`; if absent, pull that tag or configure `OLLAMA_MODEL` to an installed compatible model. Model size affects speed and memory. Verify behavior with representative English/Hindi text before using it.

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
- Do not claim a language/pair is supported until it has been explicitly registered and evaluated with the configured model.
- Avoid logging API keys, request bodies, or complete user texts. Use secret management and HTTPS for hosted deployments.

## 11. Research scope

This section proposes research work; it does not claim that an evaluation has been completed.

### Research questions

1. How accurate and meaning-preserving are local and hosted model outputs for English↔Hindi across everyday, formal, casual, idiomatic, and technical text?
2. How often does model-assisted language detection choose the correct registered language, and how does it behave on mixed-language, short, or ambiguous input?
3. Do Natural, Formal, Casual, and Literal styles create reliably distinguishable register changes without changing factual meaning?
4. Do alternative translations provide useful nuance rather than duplicates or semantic drift?
5. How useful and faithful are grammar corrections, explanations, and colloquial transliterations to target users?
6. What are the latency, memory, privacy, and cost trade-offs between local Ollama models and explicitly configured hosted inference?

### Suggested methodology

- Create a consented, anonymized evaluation set with balanced text categories and documented source/target references. Do not use private production inputs as research data without explicit consent and governance.
- Use bilingual reviewers for adequacy, fluency, terminology, tone, and meaning preservation; blind reviewers to the model/provider where practical.
- Measure task-specific outcomes: translation adequacy/fluency and terminology consistency; detection accuracy and abstention; grammar correction precision and meaning preservation; explanation faithfulness; alternative diversity/semantic equivalence; transliteration readability/pronunciation.
- Record provider/model version, quantization, hardware, prompt/style, input size, latency, failures, and configuration. Do not publish API keys or personal text.
- Report sample selection, reviewer instructions, disagreements, limitations, and confidence intervals. Automated metrics may supplement, but should not replace, bilingual human review.
- Benchmark local and hosted routes separately and document the provider's applicable data-use terms. Do not describe a model as “tested” unless the tested version, languages, dataset, and evaluation are reported.

### Out of scope until separately approved

- Advertising support for additional languages or regional variants without evaluation.
- High-stakes legal, medical, immigration, or official certified translation.
- User accounts, server-side translation history, collaboration, or cloud synchronization.
- Training or fine-tuning models on user content.
- Claims of deterministic transliteration from the current AI transliteration path.

