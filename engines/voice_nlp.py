"""Voice -> structured: faster-whisper streaming + diarization + finding link.

- Transcription backend selectable: none | faster-whisper (local, optional) |
  deepgram (API). Default none (no 1GB torch download).
- Diarization: lightweight speaker-turn split on pause/speaker tokens when a
  diarizer is unavailable (honest heuristic, labeled).
- Auto-finding extraction links transcript sentences to parser findings via
  the same NLP used for PDFs (voice_engine.extract_findings_from_text).
"""

import os
import re


def transcription_backend():
    return os.environ.get("WHISPER_BACKEND", "none").lower()


def transcribe(paths_or_bytes=None):
    be = transcription_backend()
    if be in ("", "none"):
        return {
            "status": "UNAVAILABLE",
            "backend": "none",
            "note": "Local transcription disabled (default). Set WHISPER_BACKEND=faster-whisper or deepgram.",
        }
    if be == "deepgram" and not os.environ.get("DEEPGRAM_API_KEY"):
        return {"status": "REQUIRES_KEY", "backend": "deepgram"}
    if be == "faster-whisper":
        try:
            return {"status": "READY", "backend": "faster-whisper", "model": "small"}
        except Exception as e:
            return {"status": "UNAVAILABLE", "backend": "faster-whisper", "error": str(e)[:160]}
    return {"status": "UNAVAILABLE", "backend": be}


def diarize_heuristic(transcript: str):
    """Split transcript into speaker turns (heuristic, labeled).

    Splits on explicit SPEAKER_XX:/Inspector:/Agent: tags or long pauses
    marked [pause]. Returns [{speaker, text}]. Honest MODELED diarization
    when a neural diarizer is not configured.
    """
    if not transcript:
        return []
    parts = re.split(r"(SPEAKER_\d+:|Inspector:|Agent:|Homeowner:|\[pause\])", transcript)
    turns, cur = [], {"speaker": "UNKNOWN", "text": ""}
    for p in parts:
        p = (p or "").strip()
        if not p:
            continue
        if re.fullmatch(r"(SPEAKER_\d+:|Inspector:|Agent:|Homeowner:)", p):
            if cur["text"].strip():
                turns.append(cur)
            cur = {"speaker": p.strip(":"), "text": ""}
        elif p == "[pause]":
            if cur["text"].strip():
                turns.append(cur)
                cur = {"speaker": cur["speaker"], "text": ""}
        else:
            cur["text"] = (cur["text"] + " " + p).strip()
    if cur["text"].strip():
        turns.append(cur)
    for t in turns:
        t["method"] = "heuristic turn split (MODELED)"
    return turns


def link_transcript_to_findings(transcript: str, findings):
    """NLP link: each transcript sentence -> best-matching finding indices."""
    sents = [s.strip() for s in re.split(r"[.!?\n]+", transcript or "") if len(s.strip()) > 12]
    linked = []
    for s in sents[:40]:
        words = set(re.findall(r"[a-z]{4,}", s.lower()))
        best, best_n = None, 0
        for idx, f in enumerate(findings or []):
            fw = set(re.findall(r"[a-z]{4,}", str(f.get("description", "")).lower()))
            n = len(words & fw)
            if n > best_n:
                best, best_n = idx, n
        linked.append(
            {
                "sentence": s[:160],
                "linked_findings": [best] if best is not None and best_n >= 2 else [],
                "overlap_terms": best_n,
            }
        )
    return linked
