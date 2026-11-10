
import base64
import os
import tempfile
import time

import gradio as gr
import requests
from google import genai

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
GNANI_API_KEY = os.environ.get("GNANI_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
STT_MODEL = None            # None = Prisma v2.5 (default); "prisma-v3.0" to try v3
TTS_MODEL = "timbre-v2.5"
TTS_VOICE = "Nalini"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

LANG_MAP = {
    "Hindi": "hi-IN", "English": "en-IN", "Tamil": "ta-IN", "Telugu": "te-IN",
    "Kannada": "kn-IN", "Malayalam": "ml-IN", "Bengali": "bn-IN",
    "Marathi": "mr-IN", "Gujarati": "gu-IN",
}

# Same voice pipeline, different "skills". Shows the project is a platform, not a one-trick demo.
PERSONAS = {
    "Mythology Guide": "You are a warm cross-cultural mythology and heritage expert.",
    "Student Tutor": "You are a patient school tutor. Explain the topic simply with one everyday example.",
    "Citizen Helper": ("You explain government services, forms and schemes in simple words for a first-time user. "
                       "If unsure, say so and tell the user to confirm at the official office or website."),
}

llm = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ------------------------------------------------------------------
# Gnani wrappers (also imported by eval.py)
# ------------------------------------------------------------------
def _post(url, **kwargs):
    """POST with one retry on timeouts, 429 and 5xx."""
    last = None
    for attempt in range(2):
        try:
            r = requests.post(url, timeout=60, **kwargs)
            if r.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1.5)
                continue
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(1.5)
    raise RuntimeError(f"Network error: {last}")


def _find_transcript(payload):
    if isinstance(payload, dict):
        for key in ("transcript", "text"):
            if isinstance(payload.get(key), str):
                return payload[key]
        for v in payload.values():
            found = _find_transcript(v)
            if found is not None:
                return found
    return None


def gnani_stt(audio_path, lang_code):
    """Gnani Prisma: audio file -> text."""
    data = {"language_code": lang_code}
    if STT_MODEL:
        data["model"] = STT_MODEL
    with open(audio_path, "rb") as f:
        r = _post(STT_URL, headers={"X-API-Key-ID": GNANI_API_KEY}, data=data, files={"audio_file": f})
    if r.status_code != 200:
        raise RuntimeError(f"STT {r.status_code}: {r.text[:400]}")
    return (_find_transcript(r.json()) or "").strip()


def gnani_tts(text, lang_code):
    """Gnani Timbre: text -> wav file path."""
    payload = {
        "text": text, "voice": TTS_VOICE, "model": TTS_MODEL, "language": lang_code, "speed": 1.0,
        "audio_config": {"sample_rate": 48000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }
    r = _post(TTS_URL, headers={"X-API-Key-ID": GNANI_API_KEY, "Content-Type": "application/json"}, json=payload)
    if r.status_code != 200:
        raise RuntimeError(f"TTS {r.status_code}: {r.text[:400]}")
    if "json" in r.headers.get("content-type", ""):
        data = r.json()
        b64 = next((data[k] for k in ("audio", "audio_content", "audio_base64", "data")
                    if isinstance(data, dict) and isinstance(data.get(k), str)), None)
        if b64 is None:
            raise RuntimeError(f"No audio in TTS JSON: {str(data)[:200]}")
        audio = base64.b64decode(b64)
    else:
        audio = r.content
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.write(audio)
    tmp.close()
    return tmp.name


# ------------------------------------------------------------------
# Agent
# ------------------------------------------------------------------
def render_log(history):
    return "\n\n".join(f"You: {t['q']}\nAI: {t['a']}" for t in history)


def agent(audio_path, in_lang, out_lang, persona, history):
    history = history or []

    def out(status, heard="", answer="", audio=None):
        return status, heard, answer, audio, history, render_log(history)

    if not GNANI_API_KEY or not GEMINI_API_KEY:
        return out("Set GNANI_API_KEY and GEMINI_API_KEY environment variables first.")
    if not audio_path:
        return out("No audio yet. Record or upload a clip first.")

    timings = {}

    # 1) Listen: Gnani Prisma
    try:
        t = time.perf_counter()
        heard = gnani_stt(audio_path, LANG_MAP[in_lang])
        timings["Prisma STT"] = time.perf_counter() - t
    except Exception as e:
        return out(f"STT failed: {e}")
    if not heard:
        return out("No speech detected. Try speaking closer to the mic.")

    # 2) Think: Gemini, with the last 3 turns as memory
    context = "\n".join(f"User: {h['q']}\nAssistant: {h['a']}" for h in history[-3:])
    prompt = (
        f"{PERSONAS[persona]}\n"
        f"Earlier conversation (may be empty):\n{context}\n\n"
        f'The user now asks in {in_lang}: "{heard}"\n'
        f"Answer entirely in {out_lang}, in at most 4 short lines. Plain text only: no markdown, no bullets, "
        "no emojis. Write numbers and dates as spoken words, because this will be read aloud."
    )
    try:
        t = time.perf_counter()
        answer = (llm.models.generate_content(model=GEMINI_MODEL, contents=prompt).text or "").strip()
        timings["Gemini"] = time.perf_counter() - t
    except Exception as e:
        return out(f"Gemini failed: {e}", heard)
    if not answer:
        return out("Gemini returned an empty answer.", heard)

    history = history + [{"q": heard, "a": answer}]

    # 3) Speak: Gnani Timbre
    try:
        t = time.perf_counter()
        wav = gnani_tts(answer, LANG_MAP[out_lang])
        timings["Timbre TTS"] = time.perf_counter() - t
    except Exception as e:
        return out(f"TTS failed: {e}", heard, answer)

    total = sum(timings.values())
    status = "Done | " + " | ".join(f"{k} {v:.1f}s" for k, v in timings.items()) + f" | total {total:.1f}s"
    return out(status, heard, answer, wav)


def clear_all():
    return [], "", "", "", None, ""


# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
langs = list(LANG_MAP)

with gr.Blocks(title="MythosConnect") as demo:
    gr.Markdown("# MythosConnect: Multilingual Voice Agent\n"
                "Speak in one Indian language, hear the answer in another. "
                "Powered by **Gnani Prisma** (speech to text) and **Gnani Timbre** (text to speech).")
    history_state = gr.State([])
    with gr.Row():
        with gr.Column():
            audio_in = gr.Audio(sources=["microphone", "upload"], type="filepath",
                                label="Ask by voice (record or upload)")
            in_lang = gr.Dropdown(langs, value="Hindi", label="I am speaking in")
            out_lang = gr.Dropdown(langs, value="English", label="Reply to me in")
            persona = gr.Dropdown(list(PERSONAS), value="Mythology Guide", label="Mode")
            with gr.Row():
                btn = gr.Button("Ask", variant="primary")
                clr = gr.Button("New conversation")
        with gr.Column():
            status = gr.Textbox(label="Status and latency")
            heard = gr.Textbox(label="What I heard (Prisma STT)")
            answer = gr.Textbox(label="Answer")
            audio_out = gr.Audio(label="Voice reply (Timbre TTS)", autoplay=True)
            log = gr.Textbox(label="Conversation so far", lines=6)

    ins = [audio_in, in_lang, out_lang, persona, history_state]
    outs = [status, heard, answer, audio_out, history_state, log]
    btn.click(agent, ins, outs)
    audio_in.stop_recording(agent, ins, outs)
    clr.click(clear_all, None, [history_state, status, heard, answer, audio_out, log])

if __name__ == "__main__":
    demo.launch(inbrowser=os.environ.get("SPACE_ID") is None)