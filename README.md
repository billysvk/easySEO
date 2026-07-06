# easySEO Viral Engine v2.0

**Δίνεις ένα YouTube URL → παίρνεις ολόκληρο viral optimization πακέτο.**

Ένα Python CLI που δουλεύει σαν ολόκληρη ομάδα από YouTube strategists: μαζεύει
ΟΛΗ τη διαθέσιμη δημόσια πληροφορία γύρω από το βίντεο (χωρίς κανένα YouTube API
key) και τη συνθέτει σε ένα πλήρες, έτοιμο-για-χρήση πακέτο βελτιστοποίησης.

## Τι κάνει σε ένα run (~5 δευτερόλεπτα συλλογή δεδομένων)

| Skill | Τι μαζεύει |
|---|---|
| **SubtitleDownloader** | Υπότιτλους/απομαγνητοφώνηση του βίντεο (el/en) |
| **URLAnalyzer** | Live τίτλο, περιγραφή, views, κρυφά tags του βίντεο |
| **ChannelAnalyzer** | Baseline καναλιού: median views, overperformers/underperformers, τι κλικάρει ΤΟ ΔΙΚΟ ΣΟΥ κοινό |
| **CompetitorAnalyzer** | Live YouTube SERP: top 8 βίντεο που κερδίζουν το keyword, με views/ηλικία/διάρκεια + κρυφά tags των top 5 + auto-computed "packaging intelligence" |
| **TrendHunter** | Πραγματικά queries από YouTube & Google autocomplete + Google Trends "trending now" (GR) — όχι εφευρημένα "keyword scores" |
| **CommentMiner** | Top σχόλια: τι συγκίνησε, τι ερωτήσεις έμειναν αναπάντητες, το λεξιλόγιο του κοινού |
| **SEOAuditor** | Ντετερμινιστικό σκορ 0-100 του τρέχοντος packaging με συγκεκριμένα FAIL points |
| **ImageProcessor / StudioStatsParser** | Retention screenshots & CSV από το Studio (προαιρετικά) |

Όλα τρέχουν **παράλληλα** (asyncio) και τροφοδοτούν το LLM (Gemini ή τοπικό
Ollama) με ένα expert blueprint βασισμένο σε **τεκμηριωμένη** γνώση του
αλγορίθμου 2026 (όχι folklore — π.χ. το "first-hour velocity" είναι επίσημα
μύθος, το Test & Compare κρίνεται από watch-time όχι CTR, τα tags είναι
σχεδόν νεκρά, το auto-dubbing δίνει >25% επιπλέον watch time).

## Τι παράγει

`workspace/outputs/<video>_SEO_PROPOSAL.md` με 12 ενότητες:

1. **Executive Strategy Brief** — διάγνωση με βάση τα δεδομένα
2. **Τίτλοι GR** — 3 ψυχολογικές γωνίες + A/B σχέδιο
3. **Τίτλοι EN** — 3 ψυχολογικές γωνίες
4. **Έτοιμη περιγραφή GR** — πλήρες κείμενο, όχι outline (hook, chapters, hashtags, music credits)
5. **Έτοιμη περιγραφή EN**
6. **Retention & Visual strategy**
7. **Thumbnail blueprint** — A/B set με prompts για Midjourney/DALL-E + Nano Banana mascot
8. **Tags & hashtags** — από πραγματικά autocomplete queries και tags των SERP winners
9. **Viral Shorts planner** — 3 κάθετα βίντεο από τα peaks του transcript
10. **Launch & Distribution Protocol** — community post, pinned comment, end screens, playlists, πολυγλωσσία, Hype CTA, checklist πρώτου 24ώρου
11. **Dead Video Revival Protocol** — τεκμηριωμένο playbook αναβίωσης + sequel/halo idea
12. **COPY-PASTE UPLOAD PACK** — τελικός τίτλος, περιγραφή, tags, pinned comment, community post → γράφεται και σε ξεχωριστό αρχείο `<video>_UPLOAD_PACK.md`

## Χρήση

```bash
# Το μόνο που χρειάζεσαι — ένα URL:
uv run python main.py "https://youtu.be/XXXXXXXXXXX"

# Συλλογή δεδομένων χωρίς LLM call (δεν χρειάζεται API key):
uv run python main.py "https://youtu.be/XXXXXXXXXXX" --dry-run

# Legacy: φάκελος με assets (screenshots, CSV, SRT, input.md)
uv run python main.py --folder my_video_folder

# Με εξωτερικό reference άρθρο & ισχυρότερο μοντέλο:
uv run python main.py "https://youtu.be/..." --url "https://blog.example.com/article" --model gemini-2.5-pro
```

Για URL mode δημιουργείται αυτόματα φάκελος `workspace/raw_inputs/video_<id>/`.
Αν θες να προσθέσεις retention screenshots ή Studio CSV, ρίξ' τα σε αυτόν τον
φάκελο και ξανατρέξε.

## Ρύθμιση

```bash
cp .env.example .env   # και συμπλήρωσε το GEMINI_API_KEY
uv sync
```

`.env` επιλογές: `AI_PROVIDER` (gemini/ollama), `GEMINI_API_KEY`, `GEMINI_MODEL`,
`OLLAMA_URL/OLLAMA_MODEL/OLLAMA_NUM_CTX`, `LLM_TEMPERATURE`, `TREND_GEO` (default GR).

## Αρχιτεκτονική

```text
easy_seo/
├── main.py                     # Entry point (URL-first CLI)
├── .gemini.md                  # Το "μυαλό": system instructions + output blueprint
├── config/settings.py          # Ρυθμίσεις & .env loading
├── src/
│   ├── cli.py                  # CLI arguments & banner
│   ├── agent/gemini_client.py  # Orchestrator: 4 φάσεις, όλα παράλληλα
│   └── skills/                 # Αυτόνομα skills (ένα αρχείο = μία ικανότητα)
│       ├── subtitle_downloader.py, srt_parser.py
│       ├── url_analyzer.py, channel_analyzer.py, competitor_analyzer.py
│       ├── trend_hunter.py, comment_miner.py, seo_auditor.py
│       ├── image_processor.py, studio_stats_parser.py
│       ├── prompt_builder.py, file_writer.py
│       └── thumbnail_strategist.py, shorts_architect.py
└── workspace/
    ├── raw_inputs/<video>/     # Αυτόματα προμηθευμένα assets ανά βίντεο
    └── outputs/                # SEO_PROPOSAL, UPLOAD_PACK, INTELLIGENCE_PROMPT
```
