# MythosConnect: Multilingual Voice Agent

Ask a mythology question out loud in one Indian language and hear the answer spoken back in another.

Built for the **Great Indian AI Internship Challenge** using **Gnani Prisma (speech to text)** and **Gnani Timbre (text to speech)**.

> Demo: _add your public link here (Hugging Face Space / video)_

---

## What it does

1. You record (or upload) a spoken question, for example in Hindi.
2. **Gnani Prisma** converts the speech to text.
3. **Gemini** answers as a cross-cultural mythology expert, in the language you choose, in at most four short lines.
4. **Gnani Timbre** converts the answer to natural speech and plays it back.

So a student can ask in Hindi and get the answer in Tamil, English, Telugu, and more, hands-free.

## Features

- Voice in (microphone or upload) and voice out, with independent input and output languages (9 Indian languages and English)
- Three modes on the same pipeline: Mythology Guide, Student Tutor, Citizen Helper
- Short conversation memory (last 3 turns) for follow-up questions
- Per-stage latency shown in the UI (Prisma, Gemini, Timbre)
- Retry on timeouts, rate limits and server errors; clear per-stage error messages
- Built-in benchmark (`eval.py`) using both Gnani models

## Why it matters (use cases)

- **Language access for learners:** mythology, folklore and cultural content is mostly written in English or a few major languages. Voice plus translation lets people explore it in their own language.
- **Low-literacy and elderly users:** no typing or reading needed; speak a question, hear an answer.
- **Cross-language storytelling:** ask in one language, listen in another, useful for families, classrooms and cultural exchange.
- **Museums, tourism and heritage sites:** a spoken guide that answers visitors' questions in their language.
- **Extendable:** swap the system prompt to build a voice tutor for any subject (history, science, civic information).

## Architecture

```
 +-----------+     audio      +----------------+    text     +-----------+
 |  Gradio   | -------------> | Gnani Prisma   | ----------> |  Gemini   |
 |  Web UI   |   (mic/upload) | (STT, Vachana) |  (question) |   (LLM)   |
 +-----------+                +----------------+             +-----------+
      ^                                                            |
      |        audio (wav)     +----------------+    text          |
      +----------------------- | Gnani Timbre   | <----------------+
                               | (TTS, Vachana) |  (answer)
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

## Project structure

```
MythosConnect/
  app.py            # pipeline, personas, memory, latency, UI
  eval.py           # Timbre -> Prisma round-trip benchmark (writes results.md)
  results.md        # latest benchmark output
  requirements.txt
  .env.example      # names of the environment variables
  .gitignore
  README.md
```

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/<your-username>/MythosConnect.git
cd MythosConnect
pip install -r requirements.txt
```

Set your keys as environment variables (never commit them).

Windows PowerShell:

```powershell
$env:GNANI_API_KEY  = "your-gnani-api-key"
$env:GEMINI_API_KEY = "your-gemini-api-key"
python app.py
```

macOS / Linux:

```bash
export GNANI_API_KEY="your-gnani-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
python app.py
```

Open `http://127.0.0.1:7860` in **Chrome** (the VS Code preview browser cannot use the microphone). Allow microphone access, record a question, and the reply appears automatically.

Get keys: Gnani API dashboard (docs at docs.gnani.ai) and Google AI Studio.

## Configuration

Edit the constants at the top of `app.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `STT_MODEL` | `None` (Prisma v2.5) | set to `"prisma-v3.0"` to try Prisma v3 |
| `TTS_MODEL` | `timbre-v2.5` | Timbre model |
| `TTS_VOICE` | `Nalini` | voice from the Gnani voice catalog |
| `GEMINI_MODEL` | `gemini-2.5-flash` | override with the `GEMINI_MODEL` env var |
| `LANG_MAP` | 9 languages | language names to Gnani language codes |

## Deploy a public demo (Hugging Face Spaces)

1. Create a new Space, SDK: **Gradio**.
2. Upload `app.py` and `requirements.txt`.
3. In Space **Settings > Variables and secrets**, add `GNANI_API_KEY` and `GEMINI_API_KEY` as secrets.
4. The Space builds and gives you a public URL.

## Benchmark: Timbre to Prisma round trip

`eval.py` speaks each test sentence with Gnani Timbre, transcribes it with Gnani Prisma, and computes word error rate (WER) against the original text. Full per-sentence output is in `results.md`.

| Language | Sentences | Mean WER (%) | Mean TTS+STT time (s) |
|---|---|---|---|
| Hindi | 3 | 8.3 | 3.6 |
| English | 3 | 5.6 | 3.4 |
| Tamil | 3 | 0.0 | 3.1 |
| Telugu | 3 | 33.3 | 4.1 |

What the numbers mean:

- 11 of 12 sentences were transcribed; one Telugu call failed with `EMPTY_AUDIO` from Prisma, which is scored as WER 1.00. The other two Telugu sentences scored 0.00. Overall WER is 11.8% counting that failure and 3.8% over the 11 successful calls.
- The two non-zero successful cases were a word split in Hindi (`sankatmochan` heard as `sankat mochan`) and one substituted word in English (`mochan` heard as `mokhan`).
- Caveats: only 3 sentences per language, clean synthetic speech from the same vendor, and one voice. Treat this as a consistency check, not a production accuracy claim. Real human and noisy recordings were not tested.
- After this run, `gnani_tts` was changed to retry once and raise an error if the audio is empty or truncated. Re-run `python eval.py` to refresh the table.

## Limitations

- Answer quality depends on the LLM; mythology facts should be verified for serious use.
- Language support is limited to what Prisma and Timbre support; check docs.gnani.ai for the current list.
- Each request makes three network calls, so response time depends on all three services.
- Not yet streaming; the full answer is generated before audio plays.
- Conversation memory keeps only the last 3 turns, in memory for the current session.

## Roadmap

- Streaming TTS for lower latency
- Conversation memory for follow-up questions
- Source-grounded answers (retrieval over curated texts)
- Voice and speed selection in the UI
- Use Gnani Evon as the reasoning model

## Tech stack

Python, Gradio, Requests, Google Gemini (`google-genai`), Gnani Prisma, Gnani Timbre.

## Acknowledgements

Built using Gnani.ai's Vachana speech APIs for the Great Indian AI Internship Challenge.

## License

MIT (add a `LICENSE` file if you want to open-source it).
