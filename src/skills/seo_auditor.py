"""SEOAuditor — deterministic packaging audit & viral-readiness score.

Scores the video's CURRENT packaging (title, description, tags, transcript
coverage) against 2026 YouTube packaging standards, entirely offline.
The resulting scorecard is printed for the creator AND injected into the
LLM prompt so the proposal explicitly attacks every weak point.
"""

import re

MAX_TITLE_LEN = 60
HOOK_WINDOW = 150

_POWER_WORDS = {
    "secret", "never", "nobody", "truth", "mistake", "warning", "finally",
    "insane", "shocking", "ultimate", "hidden", "banned", "exposed",
    "μυστικό", "κανείς", "αλήθεια", "λάθος", "προσοχή", "απίστευτο",
    "κρυμμένο", "σοκ", "τελικά", "μοναδικό",
}


class SEOAuditor:
    def audit(
        self,
        title: str,
        description: str,
        keyword: str,
        tags: list,
        transcript_text: str,
    ) -> dict:
        """Returns {'score': int 0-100, 'report': str} for prompt injection."""
        checks = []  # (passed, weight, label, advice-if-failed)
        title = (title or "").strip()
        description = (description or "").strip()
        primary_kw = (keyword or "").split(",")[0].strip().lower()

        # --- Title checks (40 pts) ---
        checks.append((
            bool(title), 5, "Title exists",
            "No title draft found - the proposal must create one from scratch.",
        ))
        checks.append((
            bool(title) and len(title) <= MAX_TITLE_LEN, 10,
            f"Title <= {MAX_TITLE_LEN} chars (mobile-safe)",
            f"Title is {len(title)} chars - it gets truncated on mobile search/home feeds.",
        ))
        checks.append((
            bool(primary_kw) and primary_kw in title.lower(), 10,
            "Focus keyword inside the title",
            "The focus keyword is missing from the title - zero semantic match with the target search.",
        ))
        checks.append((
            any(w in title.lower() for w in _POWER_WORDS), 5,
            "Title contains an emotional power word",
            "Title has no emotional trigger - flat titles lose the CTR battle.",
        ))
        checks.append((
            bool(title) and not re.search(r"#\d+|episode|ep\.|μερος|μέρος", title.lower()), 10,
            "Title avoids generic series formats (#3, Ep., Part)",
            "Generic series numbering kills CTR for non-subscribers - rewrite as a hook.",
        ))

        # --- Description checks (35 pts) ---
        first_lines = description[:HOOK_WINDOW].lower()
        checks.append((
            len(description) >= 200, 10,
            "Description has real length (>= 200 chars)",
            f"Description is only {len(description)} chars - YouTube has almost nothing to index.",
        ))
        checks.append((
            bool(primary_kw) and primary_kw in first_lines, 10,
            "Focus keyword inside the first 150 chars (above the fold)",
            "The keyword is not in the search-preview area of the description.",
        ))
        checks.append((
            bool(re.search(r"\b\d{1,2}:\d{2}\b", description)), 10,
            "Timestamps / chapters present",
            "No chapters found - chapters boost key-moments indexing and retention.",
        ))
        checks.append((
            "http" in description.lower() or "@" in description, 5,
            "Links / CTAs present in description",
            "No links or CTA - lost chance to route traffic (playlists, socials, subscribe).",
        ))

        # --- Tags / semantic checks (15 pts) ---
        checks.append((
            len(tags) >= 5, 10,
            "At least 5 tags defined",
            f"Only {len(tags)} tag(s) found - the semantic footprint is too small.",
        ))
        checks.append((
            bool(primary_kw) and any(primary_kw in t.lower() for t in tags), 5,
            "Focus keyword present in tags",
            "Focus keyword missing from tags.",
        ))

        # --- Transcript alignment (10 pts) ---
        transcript_lower = (transcript_text or "").lower()
        checks.append((
            bool(primary_kw) and bool(transcript_lower) and primary_kw in transcript_lower, 10,
            "Focus keyword actually spoken in the video (semantic alignment)",
            "The keyword is never spoken in the video - YouTube's ASR indexing won't connect them; consider a keyword the video truly covers.",
        ))

        score = sum(weight for passed, weight, _, _ in checks if passed)
        max_score = sum(weight for _, weight, _, _ in checks)
        score_pct = round(100 * score / max_score)

        lines = [f"CURRENT PACKAGING SCORE: {score_pct}/100"]
        failed = [c for c in checks if not c[0]]
        passed = [c for c in checks if c[0]]
        if failed:
            lines.append("WEAK POINTS THE PROPOSAL MUST FIX (each one costs discoverability):")
            lines += [f"- [FAIL, -{w}pts] {label}: {advice}" for _, w, label, advice in failed]
        if passed:
            lines.append("ALREADY STRONG (preserve these in the rewrite):")
            lines += [f"- [OK] {label}" for _, _, label, _ in passed]

        report = "\n".join(lines)
        print(f"[+] [Skill: SEOAuditor] Current packaging viral-readiness score: {score_pct}/100 "
              f"({len(failed)} weak points detected)")
        return {"score": score_pct, "report": report}
