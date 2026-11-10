# MythosConnect: Multilingual Voice Agent

Speak a question in one Indian language and hear the answer in another. No typing, no reading.

Built for the **Great Indian AI Internship Challenge** by Gnani.ai on **Gnani Prisma** (speech to text) and **Gnani Timbre** (text to speech).

| | |
|---|---|
| One-page solution pitch | [Solution_Pitch.pdf](Solution_Pitch.pdf) |
| Technical report (5 pages) | [MythosConnect_Technical_Report.pdf](MythosConnect_Technical_Report.pdf) |
| Demo video (2-3 min) | <ADD VIDEO LINK> |
| Live demo (optional) | <ADD LINK OR DELETE THIS ROW> |
| Author | Aahant Kumar, Delhi Technological University (DTU) |

---

## Gnani models used

| Model | Role in the app |
|---|---|
| **Gnani Prisma** (STT) | Transcribes the user's recorded or uploaded speech in the chosen input language |
| **Gnani Timbre** (TTS, `timbre-v2.5`) | Speaks the answer back in the chosen output language |

A general-purpose LLM (Google Gemini) writes the answer between the two Gnani calls. Gnani Evon is **not** used yet; replacing Gemini with Evon is on the roadmap.

## How it works

1. You record or upload a spoken question and pick the input and output languages.
2. **Prisma** converts the speech to text.
3. **Gemini** answers in the output language, in at most four short lines, using the selected mode and the last three turns of conversation.
4. **Timbre** converts the answer to speech and the app plays it.

## Features

- Voice in (microphone or upload) and voice out, with independent input and output languages (8 Indian languages and English configured)
- Three modes on one pipeline: **Mythology Guide**, **Student Tutor**, **Citizen Helper** (plain-language help with services and forms; the prompt tells the model to admit uncertainty and point to official sources)
- Short conversation memory (last 3 turns) for follow-up questions
- Per-stage latency shown in the UI (Prisma, Gemini, Timbre)
- Retries on timeouts, rate limits and server errors; empty or truncated TTS audio is detected and retried once
- Clear per-stage error messages that show the API's own response
- Built-in benchmark (`eval.py`) that exercises both Gnani models together

## Use cases

- **Language access for learners:** hear mythology, heritage and school topics explained in your own language.
- **Low-literacy and elderly users:** speak instead of typing and listen instead of reading.
- **Cross-language exchange:** ask in Hindi, listen in Tamil.
- **Public-service help:** spoken, simple explanations of services and forms.
- **Extensible:** a mode is only a system prompt, so new domains need no new infrastructure.

## Architecture

```
 +-----------+     wav      +----------------+  transcript  +-----------+
 |  Gradio   | -----------> | Gnani Prisma   | -----------> |  Gemini   |
 |  Web UI   | (mic/upload) | (STT, Vachana) |              |   (LLM)   |
 +-----------+              +----------------+              +-----------+
      ^                                                           |
      |        wav         +----------------+     answer text     |
      +------------------- | Gnani Timbre   | <-------------------+
                           | (TTS, Vachana) |
                           +----------------+
```

| Stage | Component | Endpoint / model |
|-------|-----------|------------------|
| Input | Gradio microphone / upload | local web UI |
| Listen | Gnani Prisma STT | `POST https://api.vachana.ai/stt/v3` |
| Think | Google Gemini | `gemini-2.5-flash` (configurable) |
| Speak | Gnani Timbre TTS | `POST https://api.vachana.ai/api/v1/tts/inference`, model `timbre-v2.5` |
| Output | Gradio audio player | autoplay |

Both Gnani calls authenticate with the `X-API-Key-ID` header.

## Benchmark: Timbre to Prisma round trip

`eval.py` speaks each test sentence with Timbre, transcribes it with Prisma, and computes word error rate (WER) against the original text. Per-sentence output is in `results.md`.

| Language | Sentences | Mean WER (%) | Mean TTS+STT time (s) |
|---|---|---|---|
| Hindi | 3 | 8.3 | 3.6 |
| English | 3 | 5.6 | 3.4 |
| Tamil | 3 | 0.0 | 3.1 |
| Telugu | 3 | 33.3 | 4.1 |

- 11 of 12 sentences were transcribed. One Telugu call failed with `EMPTY_AUDIO` from Prisma and is scored as WER 1.00; the other two Telugu sentences scored 0.00. Overall WER is **11.8%** counting that failure and **3.8%** over the 11 successful calls.
- The two non-zero successful cases were a word split in Hindi (`sankatmochan` heard as `sankat mochan`) and one substituted word in English (`mochan` heard as `mokhan`).
- Caveats: 3 sentences per language, clean synthetic speech from the same vendor, one voice. This is a consistency check, not a production accuracy claim. Real human and noisy recordings were not tested.
- After this run, `gnani_tts` was changed to retry once and raise an error on empty or truncated audio. Re-run `python eval.py` to refresh the table.

## Project structure

```
MythosConnect/
  app.py                              # pipeline, modes, memory, latency, UI
  eval.py                             # Timbre -> Prisma round-trip benchmark
  results.md                          # latest benchmark output
  Solution_Pitch.pdf                  # one-page pitch
  MythosConnect_Technical_Report.pdf  # technical report
  requirements.txt
  .gitignore
  README.md
```

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/Aahant0607/MythosConnect.git
cd MythosConnect
pip install -r requirements.txt
```

Set your keys as environment variables (never commit them).

Windows PowerShell:

```powershell
$env:GNANI_API_KEY="your-gnani-api-key"
$env:GEMINI_API_KEY="your-gemini-api-key"
python app.py
```

macOS / Linux:

```bash
export GNANI_API_KEY="your-gnani-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
python app.py
```

Open `http://127.0.0.1:7860` in **Chrome** and allow microphone access (the VS Code preview browser cannot use the microphone). To run the benchmark, use `python eval.py` with the same keys set.

Get keys from the Gnani API dashboard (docs at docs.gnani.ai) and Google AI Studio.

## Configuration

Edit the constants at the top of `app.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `STT_MODEL` | `None` (default Prisma model) | set to `"prisma-v3.0"` to try Prisma v3 |
| `TTS_MODEL` | `timbre-v2.5` | Timbre model |
| `TTS_VOICE` | `Nalini` | voice from the Gnani voice catalog |
| `GEMINI_MODEL` | `gemini-2.5-flash` | override with the `GEMINI_MODEL` env var |
| `LANG_MAP` | 9 entries | language names to Gnani language codes |
| `PERSONAS` | 3 modes | system prompts for each mode |

The benchmark covers Hindi, English, Tamil and Telugu. The other configured languages (Kannada, Malayalam, Bengali, Marathi, Gujarati) are not benchmarked; check docs.gnani.ai for the current language list.

## Deploy a public demo (Hugging Face Spaces)

1. Create a new Space with SDK **Gradio**.
2. Upload `app.py` and `requirements.txt`.
3. In **Settings > Variables and secrets**, add `GNANI_API_KEY` and `GEMINI_API_KEY` as secrets.

## Limitations

- Answer quality depends on the LLM; verify facts before relying on them, especially in Citizen Helper mode.
- Language support is limited to what Prisma and Timbre support.
- Each request makes three network calls, so response time depends on all three services.
- The full answer is generated before audio plays (no streaming yet).
- Conversation memory keeps only the last 3 turns, for the current session.
- The benchmark is small and uses synthetic speech.

## Roadmap

- Use Gnani Evon as the reasoning model so the whole pipeline runs on Gnani models
- Streaming TTS for lower latency
- Retrieval over curated sources for grounded answers
- Benchmark on recorded human speech; report character error rate as well as WER
- Voice and speed selection in the UI

## Tech stack

Python, Gradio, Requests, Google Gemini (`google-genai`), Gnani Prisma, Gnani Timbre.

## Author

Aahant Kumar, Delhi Technological University (DTU). Built for the Great Indian AI Internship Challenge by Gnani.ai.
