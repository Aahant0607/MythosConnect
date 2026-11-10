"""
Round-trip benchmark for Gnani Timbre + Prisma.

For each test sentence: Timbre (TTS) speaks it -> Prisma (STT) transcribes it -> compare with the original.
Reports Word Error Rate (WER) and latency per language, and writes results.md for your README.

Run:  python eval.py        (uses a few TTS + STT calls per sentence; needs GNANI_API_KEY)
Note: this measures how consistently the two models work together on clean synthetic speech.
      For a stronger claim, also test with real human recordings (see README tip in chat).
"""
import statistics
import string
import time

from app import LANG_MAP, gnani_stt, gnani_tts

TESTS = {
    "Hindi": ["रामायण के लेखक कौन हैं",
              "हनुमान जी को संकटमोचन क्यों कहा जाता है",
              "महाभारत का युद्ध कहाँ हुआ था"],
    "English": ["Who wrote the Ramayana",
                "Why is Hanuman called Sankat Mochan",
                "Where did the Mahabharata war take place"],
    "Tamil": ["ராமாயணத்தை எழுதியவர் யார்",
              "மகாபாரத போர் எங்கே நடந்தது",
              "விநாயகரை ஏன் முதலில் வணங்குகிறோம்"],
    "Telugu": ["రామాయణాన్ని ఎవరు రాశారు",
               "మహాభారత యుద్ధం ఎక్కడ జరిగింది",
               "వినాయకుడిని ముందుగా ఎందుకు పూజిస్తారు"],
}

PUNCT = str.maketrans("", "", string.punctuation + "।॥…")


def words(text):
    return text.translate(PUNCT).lower().split()


def wer(ref, hyp):
    r, h = words(ref), words(hyp)
    if not r:
        return 0.0
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return d[len(h)] / len(r)


def main():
    rows, details = [], []
    for lang, sentences in TESTS.items():
        code = LANG_MAP[lang]
        wers, lats = [], []
        for s in sentences:
            try:
                t = time.perf_counter()
                wav = gnani_tts(s, code)
                heard = gnani_stt(wav, code)
                lat = time.perf_counter() - t
                w = wer(s, heard)
            except Exception as e:
                heard, lat, w = f"ERROR: {e}", float("nan"), 1.0
            wers.append(w)
            lats.append(lat)
            details.append((lang, s, heard, w))
            print(f"[{lang}] WER {w:.2f} | said: {s} | heard: {heard}")
        ok = [l for l in lats if l == l]
        rows.append((lang, len(sentences), statistics.mean(wers) * 100, statistics.mean(ok) if ok else float("nan")))

    lines = ["| Language | Sentences | Mean WER (%) | Mean TTS+STT time (s) |", "|---|---|---|---|"]
    lines += [f"| {l} | {n} | {w:.1f} | {t:.1f} |" for l, n, w, t in rows]
    lines += ["", "Details:", "", "| Language | Spoken (Timbre) | Heard (Prisma) | WER |", "|---|---|---|---|"]
    lines += [f"| {l} | {s} | {h} | {w:.2f} |" for l, s, h, w in details]
    with open("results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n" + "\n".join(lines[:2 + len(rows)]))
    print("\nSaved results.md")


if __name__ == "__main__":
    main()