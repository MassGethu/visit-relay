"""Worker concerns: something she is worried about that is not on the government danger-sign checklist.

Rules only, no LLM: a concern is captured when she uses a worry word ("chinta", "चिंता", "worried"),
or when she asks for it to reach the ANM ("ANM ko batao ..."). Her words are kept verbatim.
A concern never changes a checklist state; the danger check runs on the same sentence as usual.
"""
from __future__ import annotations

from .text import tokens

ANM_WORDS = {"anm", "एएनएम", "nm", "ए.एन.एम"}
# imperative only: "ANM ko bata diya" (already told her) is not a request
TELL_WORDS = {"batao", "bataiye", "bataana", "batana", "batado", "dikhao", "dikhana", "dikhaiye",
              "बताओ", "बताइए", "बताइये", "बताना", "दिखाओ", "दिखाना", "दिखाइए", "tell", "show", "flag",
              "ತಿಳಿಸಿ", "ಹೇಳಿ", "ತೋರಿಸಿ", "tilisi", "heli"}
TELL_SEQS = [("bata", "do"), ("bata", "dena"), ("बता", "दो"), ("बता", "देना")]
FLAG_SEQS = [("flag", "karo"), ("flag", "kar", "do"), ("flag", "करो"), ("flag", "कर", "दो"), ("flag", "maadi")]
WORRY_WORDS = {"chinta", "chintaa", "चिंता", "fikar", "fikr", "फ़िक्र", "फिक्र", "concern", "concerned",
               "worried", "worry", "worrying", "shak", "शक", "ajeeb", "अजीब", "ಚಿಂತೆ", "ಆತಂಕ", "chinte"}
WORRY_SEQS = [("theek", "nahi", "lag"), ("ठीक", "नहीं", "लग"), ("dar", "lag"), ("डर", "लग")]
MIN_CONCERN_WORDS = 3          # "ANM ko batao" alone flags the last concern; longer carries its own


def _has(words: list[str], seq: tuple[str, ...]) -> bool:
    n = len(seq)
    return any(tuple(words[i:i + n]) == seq for i in range(len(words) - n + 1))


def words_of(text: str) -> list[str]:
    return [t.text for t in tokens(text)]


def is_flag_request(words: list[str]) -> bool:
    """She asks for this to reach the ANM: "ANM ko batao", "एएनएम को बताइए", "flag karo"."""
    if any(_has(words, s) for s in FLAG_SEQS):
        return True
    if not set(words) & ANM_WORDS:
        return False
    return bool(set(words) & TELL_WORDS) or any(_has(words, s) for s in TELL_SEQS)


def is_worry(words: list[str]) -> bool:
    return bool(set(words) & WORRY_WORDS) or any(_has(words, s) for s in WORRY_SEQS)


def carries_content(words: list[str]) -> bool:
    """Does a flag request also say what the concern is ("ANM ko batao ki saas khana nahi deti")?"""
    command = ANM_WORDS | TELL_WORDS | {"ko", "को", "ಗೆ", "ki", "कि", "karo", "करो", "kar", "do", "दो",
                                        "please", "zaroor", "ज़रूर", "yeh", "ye", "यह", "ये", "baat", "बात"}
    return sum(w not in command for w in words) >= MIN_CONCERN_WORDS
