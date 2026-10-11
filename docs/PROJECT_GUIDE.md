# LinguaLite: A Plain-Language Project Guide

## What is LinguaLite?

LinguaLite is a web app that helps people work with short pieces of English and Hindi text. It can translate between the two languages, suggest grammar corrections, explain wording, offer alternative translations, and convert Hindi text between Devanagari and Latin letters.

The app uses an AI model to produce results. It is an aid for understanding and drafting—not a certified translator, a language teacher, or a guarantee that every answer is correct.

## What can I do with it?

### Translate

1. Choose **Translate**.
2. Enter or paste text in the left panel.
3. Keep **Auto-detect** selected, or choose English or Hindi.
4. Choose the target language.
5. Choose a style:
   - **Natural:** fluent wording for ordinary use.
   - **Formal:** more professional or respectful wording.
   - **Casual:** more conversational wording.
   - **Literal:** stays closer to the wording of the source while aiming to remain understandable.
6. Optionally choose up to three alternatives or ask for a separate explanation.
7. Select **Translate**. Review the result before using it.

The app currently advertises English↔Hindi translation only. Auto-detection is model-assisted; if the model cannot identify English or Hindi, the app should ask you to choose a supported language or report that it cannot continue.

### Check grammar

1. Choose **Grammar**.
2. Select the source language or Auto-detect.
3. Enter your text and select **Grammar**.

The grammar task asks the model to preserve the language rather than translate. Review the correction: AI may alter wording or miss errors.

### Understand a phrase

1. Choose **Explain**.
2. Select the text's language or Auto-detect.
3. Enter the text or phrase and select **Explain**.

The explanation is shown separately from your original text. It may describe possible idioms, tone, or context, but it is not authoritative.

### Change Hindi script

1. Choose **Transliterate**.
2. Select the input script or Auto-detect, then choose Latin or Devanagari as the output script.
3. Enter Hindi text and select **Transliterate**.

Transliteration changes the writing system; it is not translation. LinguaLite asks its AI provider for colloquial Hindi romanization, so spellings can vary. It is not a deterministic pronunciation standard.

## Useful controls

- **Swap:** reverses the source and target languages when a specific source is selected. It is unavailable while Auto-detect is selected.
- **Copy:** copies the main result (or an individual alternative) to the clipboard.
- **Download:** saves the main result as a plain-text file.
- **Clear:** clears the current text and result.
- **Local history:** keeps up to 50 successful results in this browser. You can reopen or delete an entry. Clearing browser site data removes this history.

History is not uploaded just because you open or revisit an entry. If you select a task and submit text again, that new request is sent to the provider selected by the app operator.

## What happens to my text?

The app's operator configures the AI provider:

- **Ollama:** the default. Text goes to the Ollama server configured for the backend. That is only local if the operator runs Ollama on a local or trusted machine/network.
- **Gemini:** optional and must be explicitly selected by the operator. Text is sent to Google's Gemini API. The API key belongs on the server, not in the browser.

LinguaLite does not create server-side translation history. The browser history feature stores results in localStorage on the device. Avoid entering sensitive or confidential information unless you understand who operates the provider and its applicable privacy terms.

## Advantages

- One simple interface for several language tasks.
- Style choices for different translation contexts.
- Separate grammar, explanation, and transliteration tasks help keep those results distinct from translation.
- The default provider can run locally, which can avoid sending text to a hosted model when correctly configured.
- Optional Gemini access allows an operator to choose a hosted provider, with no automatic provider switching.
- Local browser history makes it easier to revisit recent results without requiring an account.
- Copy and download controls make results easy to reuse.

## Limitations

- English and Hindi are the only registered translation languages at present.
- Automatic detection depends on the selected generative model and can fail on short, mixed, or ambiguous text.
- AI can mistranslate, omit context, alter tone, or produce incorrect explanations and grammar changes.
- Alternative translations are not guaranteed to be semantically identical or genuinely distinct.
- Hindi transliteration is model-generated, colloquial, and variable.
- Local models may be slow or require substantial memory.
- Gemini access, quotas, costs, and data terms depend on Google's current policies and account configuration.
- Do not rely on the app for certified, legal, medical, safety-critical, or other high-stakes translation without qualified human review.

## Starting the app

The frontend and backend run as two separate programs.

### Start the backend

Open a terminal in the project folder:

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend serves API endpoints; it does not serve the website homepage at `/`.

### Start the website

Open a second terminal:

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open **http://127.0.0.1:5173/** in your browser. If Python reports that `uvicorn` is missing, install backend requirements into the existing virtual environment:

```bash
cd backend
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For Gemini, the operator must configure a valid `GEMINI_API_KEY` and explicitly select Gemini in the backend environment, then restart the backend. Do not put API keys in frontend settings.

## Research opportunities

LinguaLite can be a starting point for a small study of AI language tools. Possible research areas include:

1. **Translation quality:** compare English↔Hindi results for everyday, formal, casual, idiomatic, and technical text.
2. **Style usefulness:** ask bilingual reviewers whether the four styles are meaningfully different while preserving the original meaning.
3. **Automatic detection:** measure correct detection on full sentences, short phrases, mixed Hindi-English, names, and ambiguous inputs.
4. **Grammar support:** evaluate which corrections are helpful, which introduce errors, and whether meaning is preserved.
5. **Explanations and alternatives:** study clarity, usefulness, semantic faithfulness, and duplicate frequency.
6. **Transliteration:** compare readability and pronunciation expectations across users and regions.
7. **Privacy and performance:** compare local and hosted providers for latency, resource requirements, cost, and data handling.
8. **Accessibility and usability:** test whether the task labels, language controls, error messages, and history are understandable to different users.

### A responsible study plan

- Obtain consent and avoid collecting personal or confidential text.
- Create a balanced evaluation set and document how examples were selected.
- Ask bilingual reviewers to score fluency, faithfulness, tone, and terminology; do not rely only on automatic scores.
- Track exact provider/model versions, settings, hardware, latency, and failures.
- Compare alternatives and explanations against the source meaning, not just fluency.
- Report uncertainty, reviewer disagreement, and model limitations.
- Do not claim a language or task is reliable until the tested model, data, and results are documented.

## Further reading

- [Technical Documentation](./TECHNICAL_DOCUMENTATION.md) — architecture, API, configuration, tests, deployment, and research methodology.
- [Project README](../README.md) — repository setup and current implementation details.

