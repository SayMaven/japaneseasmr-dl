import re

REFERER = "https://japaneseasmr.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Regex progress parsing patterns for yt-dlp and aria2c output
RE_YTDLP_PROGRESS = re.compile(
    r'\[download\]\s+([\d\.]+)%\s+of\s+~?\s*([\d\.]+[kMGTP]?i?B)(?:\s+at\s+([\d\.]+[kMGTP]?i?B/s))?(?:\s+ETA\s+([\d:]+))?(?:\s*\(frag\s+(\d+)/(\d+)\))?',
    re.IGNORECASE,
)
RE_ARIA2_PROGRESS = re.compile(
    r'\[#\w+\s+([\d\.]+[kMGTP]?i?B)/([\d\.]+[kMGTP]?i?B)\s*\(([\d\.]+)%\).*?DL:([\d\.]+[kMGTP]?i?B).*?ETA:([^\s\]]+)\]',
    re.IGNORECASE,
)
RE_FRAG_PROGRESS = re.compile(
    r'\[download\]\s+Downloading\s+(?:item|fragment)\s+(\d+)\s+of\s+(\d+)',
    re.IGNORECASE,
)

