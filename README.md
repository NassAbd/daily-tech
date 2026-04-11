# Echo-Tech Daily 🎙️

> **Votre briefing quotidien sur l'Intelligence Artificielle**, récupéré, synthétisé en français et lu par une IA — automatiquement chaque matin à 07:00 UTC.

---

## Comment ça fonctionne ?

```
TechCrunch RSS (IA)
      │
      ▼
feedparser — filtre les 24 dernières heures
      │
      ▼
Gemini 2.5 Flash — résumé & traduction en français (briefing radio)
      │
      ▼
Gemini TTS — synthèse vocale → audio/latest_report.wav
      │
      ▼
data.json — date, titre, résumé, nombre d'articles
      │
      ▼
GitHub Pages — index.html charge data.json et diffuse l'audio
```

---

## ⚙️ Configuration initiale

### Étape 1 — Forker / Cloner ce dépôt

```bash
git clone https://github.com/VOTRE-USERNAME/dailytech.git
cd dailytech
```

### Étape 2 — Ajouter la clé API Gemini dans les secrets GitHub

1. Rendez-vous sur **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)** et générez une clé API.
2. Dans votre dépôt GitHub, allez dans **Settings → Secrets and variables → Actions**.
3. Cliquez sur **"New repository secret"** et créez :

| Nom | Valeur |
|-----|--------|
| `GEMINI_API_KEY` | `votre-clé-api-gemini` |

### Étape 3 (Optionnel) — Variables d'environnement configurables

Dans **Settings → Secrets and variables → Actions → Variables**, vous pouvez ajouter :

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `TTS_VOICE_NAME` | `Charon` | Voix TTS : `Charon` (M), `Kore` (F), `Aoede` (F), `Lede` (F) |
| `MAX_ARTICLES` | `10` | Nombre maximum d'articles à traiter |

### Étape 4 — Activer GitHub Pages

1. Dans votre dépôt, allez dans **Settings → Pages**.
2. Sous **"Source"**, sélectionnez **"Deploy from a branch"**.
3. Choisissez la branche **`main`** et le dossier **`/ (root)`**.
4. Cliquez sur **"Save"**.

Votre site sera accessible à l'adresse :
```
https://VOTRE-USERNAME.github.io/dailytech/
```

---

## 🚀 Déclenchement manuel

Pour forcer la génération d'un briefing immédiatement sans attendre 07:00 UTC :

1. Allez dans l'onglet **Actions** de votre dépôt.
2. Sélectionnez le workflow **"Echo-Tech Daily — Briefing IA Quotidien"**.
3. Cliquez sur **"Run workflow"** → **"Run workflow"**.

---

## 🛠️ Développement local

### Prérequis
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installé (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Installation

```bash
# Installer les dépendances
uv sync

# Copier le fichier d'environnement
cp .env.example .env
# Éditer .env et renseigner GEMINI_API_KEY
```

### Exécution

```bash
# Mode production (appels API réels)
uv run python scripts/main.py

# Mode hors-ligne / test (aucun appel API)
uv run python scripts/main.py --dry-run
```

### Vérification de la qualité du code

```bash
# Type check
uvx ty check scripts/main.py

# Lint
uvx ruff check scripts/
```

---

## 📁 Structure du projet

```
dailytech/
├── .github/
│   └── workflows/
│       └── daily_report.yml   # Cron GitHub Actions (07:00 UTC)
├── audio/
│   └── latest_report.wav      # Audio généré (mis à jour quotidiennement)
├── scripts/
│   └── main.py                # Pipeline principal
├── index.html                 # Frontend statique (Podcast App)
├── data.json                  # Données du dernier briefing
├── pyproject.toml             # Projet uv
├── .env.example               # Template des variables d'environnement
└── README.md
```

---

## 📝 Licence

MIT — Libre d'utilisation et de modification.
