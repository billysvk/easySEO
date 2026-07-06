"""CommentMiner — mines the video's own comments for audience intelligence.

Comments are the rawest audience-voice data on YouTube and no mainstream
tool pipelines them into packaging decisions. This skill downloads the top
comments (keyless, via the InnerTube endpoints wrapped by
youtube-comment-downloader) and distills:

- the most-liked comments (what resonated — social proof to amplify)
- every question asked (unmet curiosity -> next-video ideas & FAQ pins)
- the audience's actual vocabulary (mirror it in titles/descriptions)
"""

import asyncio
import re
from collections import Counter

try:
    from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
except ImportError:
    YoutubeCommentDownloader = None
    SORT_BY_POPULAR = 0

MAX_COMMENTS = 60
_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "this", "that", "have", "was",
    "από", "και", "για", "στο", "στη", "στην", "τον", "την", "του", "της",
    "τα", "το", "μου", "σου", "σας", "μας", "ένα", "μια", "είναι", "ειναι",
    "που", "πολύ", "πολυ", "δεν", "θα", "να", "με", "σε", "τι", "οτι", "ότι",
}


class CommentMiner:
    async def mine(self, video_url: str) -> str:
        """Downloads and distills top comments. Returns a text report."""
        if not video_url:
            return "No video URL — comment mining skipped."
        if YoutubeCommentDownloader is None:
            return "youtube-comment-downloader not installed — comment mining skipped."

        print(f"[*] [Skill: CommentMiner] Mining top comments for audience intelligence...")
        try:
            comments = await asyncio.to_thread(self._download, video_url)
        except Exception as e:
            print(f"[-] [Skill: CommentMiner] Comment download failed: {e}")
            return f"Comment mining failed: {e}"

        if not comments:
            return "No comments found (new video or comments disabled)."

        print(f"[+] [Skill: CommentMiner] Mined {len(comments)} top comments.")
        return self._build_report(comments)

    @staticmethod
    def _download(video_url: str) -> list:
        downloader = YoutubeCommentDownloader()
        comments = []
        for comment in downloader.get_comments_from_url(video_url, sort_by=SORT_BY_POPULAR):
            comments.append(
                {
                    "text": (comment.get("text") or "").strip(),
                    "votes": comment.get("votes", "0"),
                    "author": comment.get("author", ""),
                }
            )
            if len(comments) >= MAX_COMMENTS:
                break
        return comments

    def _build_report(self, comments: list) -> str:
        top = comments[:8]
        questions = [c for c in comments if "?" in c["text"] or ";" in c["text"]][:8]

        word_counter: Counter = Counter()
        for c in comments:
            for word in re.findall(r"[\w']+", c["text"].lower()):
                if len(word) > 3 and word not in _STOPWORDS:
                    word_counter[word] += 1
        vocabulary = [f"{w} (x{n})" for w, n in word_counter.most_common(15) if n >= 2]

        lines = [f"AUDIENCE VOICE — mined from the video's top {len(comments)} comments:"]
        if top:
            lines.append("MOST-LIKED COMMENTS (what resonated — candidates for pinned-comment replies & community posts):")
            lines += [f"- [{c['votes']} likes] {self._clip(c['text'])}" for c in top]
        if questions:
            lines.append("QUESTIONS THE AUDIENCE ASKED (unmet curiosity — answer in the pinned comment, description FAQ, or the next video):")
            lines += [f"- {self._clip(c['text'])}" for c in questions]
        if vocabulary:
            lines.append("AUDIENCE VOCABULARY (their actual words — mirror them in titles/descriptions): " + ", ".join(vocabulary))
        return "\n".join(lines)

    @staticmethod
    def _clip(text: str, limit: int = 220) -> str:
        text = re.sub(r"\s+", " ", text)
        return text[:limit] + ("..." if len(text) > limit else "")
