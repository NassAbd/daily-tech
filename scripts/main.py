"""
Echo-Tech Daily — Pipeline principal
=====================================
Flux : TechCrunch RSS (IA) → Gemini 2.5 Flash (résumé FR) → Gemini TTS (WAV) → data.json

Usage:
    uv run python scripts/main.py           # Production
    uv run python scripts/main.py --dry-run # Mode hors-ligne (fixture locale)

Type check : uvx ty check scripts/main.py
Lint       : uvx ruff check scripts/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict

import feedparser
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

RSS_URL = "https://techcrunch.com/category/artificial-intelligence/feed/"
TEXT_MODEL = "gemini-2.5-flash"
TTS_MODEL = "gemini-2.5-flash-preview-tts"
AUDIO_PATH = Path("audio/latest_report.wav")
DATA_JSON_PATH = Path("data.json")
WINDOW_HOURS = 24
DEFAULT_VOICE = "Charon"

# ---------------------------------------------------------------------------
# Schéma de données (Contract-First)
# ---------------------------------------------------------------------------


class ArticleItem(TypedDict):
    title: str
    summary: str
    link: str
    published: str


class DailyReport(TypedDict):
    date: str
    title: str
    summary: str
    article_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _struct_to_dt(struct_time: time.struct_time) -> datetime:
    """Convertit un struct_time (feedparser) en datetime UTC aware."""
    return datetime(*struct_time[:6], tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Étape 1 — Récupération du flux RSS
# ---------------------------------------------------------------------------


def fetch_recent_articles(rss_url: str, window_hours: int = WINDOW_HOURS) -> list[ArticleItem]:
    """
    Récupère les articles publiés durant les `window_hours` dernières heures.
    Retourne une liste d'ArticleItem triée du plus récent au plus ancien.
    """
    print(f"[RSS] Fetching feed: {rss_url}")
    feed = feedparser.parse(rss_url)

    if feed.bozo:
        # bozo=True indique une erreur de parsing, mais les entrées peuvent quand même exister
        print(f"[RSS] Warning: feed parsed with errors — {feed.bozo_exception}")

    cutoff = _utcnow() - timedelta(hours=window_hours)
    articles: list[ArticleItem] = []

    for entry in feed.entries:
        if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
            continue
        published_dt = _struct_to_dt(entry.published_parsed)
        if published_dt < cutoff:
            continue

        articles.append(
            ArticleItem(
                title=entry.get("title", "Sans titre"),
                summary=entry.get("summary", entry.get("description", "")),
                link=entry.get("link", ""),
                published=published_dt.isoformat(),
            )
        )

    articles.sort(key=lambda a: a["published"], reverse=True)
    print(f"[RSS] {len(articles)} article(s) trouvé(s) dans les {window_hours} dernières heures.")
    return articles


def _build_articles_text(articles: list[ArticleItem]) -> str:
    """Formate les articles en bloc de texte pour le prompt Gemini."""
    lines: list[str] = []
    for i, art in enumerate(articles, start=1):
        lines.append(f"### Article {i} — {art['title']}")
        lines.append(f"Publié : {art['published']}")
        lines.append(f"Lien : {art['link']}")
        lines.append(art["summary"])
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Étape 2 — Résumé & traduction via Gemini Flash
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Tu es un présentateur radio professionnel, dynamique et passionné par la technologie.
Ta mission : rédiger un briefing matinal IA en français, fluide et captivant,
à partir des articles fournis. Le briefing doit :
- Commencer par une accroche percutante
  (ex : "Bonjour et bienvenue dans votre briefing IA du [date]...")
- Présenter chaque actualité de façon concise, claire et engageante
- Utiliser un registre journalistique oral (phrases courtes, transitions naturelles)
- Se terminer par une formule de clôture chaleureuse
- Être ENTIÈREMENT en français, sans aucun mot anglais sauf les noms propres
Tu NE dois PAS inventer d'informations : base-toi uniquement sur les articles fournis.
"""


def generate_briefing(client: genai.Client, articles: list[ArticleItem]) -> str:
    """
    Envoie les articles à Gemini 2.5 Flash et retourne le texte du briefing en français.
    """
    today_str = _utcnow().strftime("%d %B %Y")
    articles_text = _build_articles_text(articles)

    user_message = (
        f"Date du jour : {today_str}\n\n"
        f"Voici {len(articles)} articles IA publiés ces dernières 24 heures :\n\n"
        f"{articles_text}\n\n"
        "Génère le briefing matinal radio en français."
    )

    print(f"[LLM] Génération du briefing avec {TEXT_MODEL}...")
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=4096,
        ),
    )

    if response.text is None:
        raise ValueError("[LLM] Erreur : La réponse de Gemini ne contient pas de texte.")
    briefing = response.text.strip()
    print(f"[LLM] Briefing généré ({len(briefing)} caractères).")
    return briefing


# ---------------------------------------------------------------------------
# Étape 3 — Synthèse vocale via Gemini TTS
# ---------------------------------------------------------------------------


def _save_wav(path: Path, pcm_data: bytes) -> None:
    """Sauvegarde les données PCM brutes dans un fichier WAV (mono, 24kHz, 16-bit)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(24000)
        wf.writeframes(pcm_data)
    print(f"[TTS] Audio sauvegardé : {path} ({path.stat().st_size / 1024:.1f} KB)")


def generate_audio(
    client: genai.Client, briefing_text: str, voice_name: str = DEFAULT_VOICE
) -> None:
    """
    Transforme le texte du briefing en audio WAV via Gemini TTS.
    """
    print(f"[TTS] Synthèse vocale avec {TTS_MODEL} (voix: {voice_name})...")
    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=briefing_text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    )
                )
            ),
        ),
    )

    candidates = response.candidates
    assert candidates, "[TTS] Erreur : aucun candidat dans la réponse TTS."

    content = candidates[0].content
    if content is None or content.parts is None:
        raise ValueError("[TTS] Erreur : contenu ou parties manquantes dans la réponse TTS.")

    parts = content.parts
    if not parts or parts[0].inline_data is None:
        raise ValueError("[TTS] Erreur : aucune donnée inline dans la réponse TTS.")

    pcm_data = parts[0].inline_data.data
    if pcm_data is None:
        raise ValueError("[TTS] Erreur : données audio (bytes) vides.")

    _save_wav(AUDIO_PATH, pcm_data)


# ---------------------------------------------------------------------------
# Étape 4 — Export data.json
# ---------------------------------------------------------------------------


def write_data_json(articles: list[ArticleItem], briefing_text: str) -> DailyReport:
    """
    Génère et écrit `data.json` avec les métadonnées du briefing du jour.
    """
    now = _utcnow()
    day_fr = now.strftime("%d %B %Y")

    report: DailyReport = {
        "date": now.isoformat(),
        "title": f"Briefing IA du {day_fr}",
        "summary": briefing_text,
        "article_count": len(articles),
    }

    DATA_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[JSON] data.json mis à jour ({report['article_count']} articles).")
    return report


# ---------------------------------------------------------------------------
# Fixture hors-ligne (--dry-run)
# ---------------------------------------------------------------------------

DRY_RUN_ARTICLES: list[ArticleItem] = [
    ArticleItem(
        title="OpenAI unveils GPT-Next with multimodal reasoning",
        summary=(
            "OpenAI has announced its next-generation model featuring "
            "advanced multimodal capabilities..."
        ),
        link="https://techcrunch.com/dry-run-1",
        published=_utcnow().isoformat(),
    ),
    ArticleItem(
        title="Google DeepMind releases Gemini Ultra 3",
        summary=(
            "Google DeepMind's latest Gemini model scores top marks on "
            "MMLU and coding benchmarks..."
        ),
        link="https://techcrunch.com/dry-run-2",
        published=_utcnow().isoformat(),
    ),
]


def dry_run() -> None:
    """Mode hors-ligne : génère un data.json de test sans appeler l'API."""
    print("[DRY-RUN] Mode hors-ligne activé — aucun appel API.")
    fake_briefing = (
        "Bonjour et bienvenue dans ce briefing de test ! "
        "Aujourd'hui, deux grandes annonces dans le monde de l'IA... "
        "Ceci est un texte de démonstration généré sans appel API. Bonne journée !"
    )
    report = write_data_json(DRY_RUN_ARTICLES, fake_briefing)
    print(f"[DRY-RUN] Rapport fictif généré : {report['title']}")
    print("[DRY-RUN] Note : aucun fichier audio produit en mode --dry-run.")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Echo-Tech Daily pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode hors-ligne : génère un data.json fictif sans appeler l'API Gemini.",
    )
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERREUR] La variable d'environnement GEMINI_API_KEY est manquante.", file=sys.stderr)
        sys.exit(1)

    voice_name = os.getenv("TTS_VOICE_NAME", DEFAULT_VOICE)
    max_articles = int(os.getenv("MAX_ARTICLES", "10"))

    client = genai.Client(api_key=api_key)

    # --- Étape 1 : RSS ---
    articles = fetch_recent_articles(RSS_URL)

    if not articles:
        print("[WARN] Aucun article trouvé dans les 24 dernières heures. Pipeline arrêté.")
        sys.exit(0)

    articles = articles[:max_articles]

    # --- Étape 2 : Briefing textuel ---
    briefing_text = generate_briefing(client, articles)

    # --- Étape 3 : Synthèse vocale ---
    generate_audio(client, briefing_text, voice_name=voice_name)

    # --- Étape 4 : Export JSON ---
    write_data_json(articles, briefing_text)

    print("[OK] Pipeline Echo-Tech Daily terminé avec succès.")


if __name__ == "__main__":
    main()
