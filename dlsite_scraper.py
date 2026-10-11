import html
import re
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def sanitize_filename(name):
    """Membersihkan karakter yang dilarang pada sistem file Windows."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().rstrip(".")
    return clean if clean else "audio"


def fetch_dlsite_metadata(rj_id):
    """Mengambil metadata karya (Judul, CV, Circle, Genre, Rating) langsung dari DLsite resmi."""
    clean_id = rj_id.strip().upper()
    info = {
        "title": clean_id,
        "cv": "-",
        "circle": "-",
        "genre": "-",
        "age_rating": "-",
        "cover_url": f"https://pic.weeabo0.xyz/{clean_id}_img_main.jpg",
    }
    urls = [
        f"https://www.dlsite.com/maniax/work/=/product_id/{clean_id}.html",
        f"https://www.dlsite.com/home/work/=/product_id/{clean_id}.html",
        f"https://www.dlsite.com/girls/work/=/product_id/{clean_id}.html",
        f"https://www.dlsite.com/pro/work/=/product_id/{clean_id}.html",
    ]

    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Cookie": "adultchecked=1; locale=ja_JP",
                },
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                page_html = resp.read().decode("utf-8", errors="ignore")

            # 1. Ambil Judul
            title_match = re.search(r'<meta itemprop="name" content="(.*?)">', page_html)
            if not title_match:
                title_match = re.search(r'id=["\']work_name["\'][^>]*>(.*?)</h1>', page_html, re.DOTALL)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', page_html, re.DOTALL)
            if title_match:
                raw_title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
                raw_title = re.sub(r"\s*\[[^\]]+\]\s*\|\s*DLsite.*$", "", raw_title)
                raw_title = raw_title.replace(" | DLsite", "").replace(" - DLsite", "").strip()
                info["title"] = html.unescape(raw_title)

            # 2. Ambil Circle / Maker
            maker_match = re.search(r'<th>\s*(?:サークル名|ブランド名|メーカー名|著者)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if maker_match:
                makers = re.findall(r'<a[^>]*>(.*?)</a>', maker_match.group(1), re.DOTALL)
                clean_makers = [re.sub(r'<[^>]+>', '', m).strip() for m in makers if re.sub(r'<[^>]+>', '', m).strip()]
                if clean_makers:
                    info["circle"] = html.unescape(", ".join(clean_makers))

            if info["circle"] == "-":
                brand_match = re.search(r'<div itemprop="brand"[^>]*>.*?<meta itemprop="name" content="(.*?)">', page_html, re.DOTALL)
                if not brand_match:
                    brand_match = re.search(r'"position":\s*3,\s*"name":\s*"([^"]+)"', page_html)
                if not brand_match:
                    # Ambil dari tag <title> ... [Circle] | DLsite ...
                    t_match = re.search(r'\[(.*?)\]\s*\|\s*DLsite', page_html)
                    if t_match:
                        brand_match = t_match

                if brand_match:
                    raw_brand = html.unescape(brand_match.group(1).strip())
                    if "/" in raw_brand:
                        parts = raw_brand.split("/", 1)
                        info["circle"] = parts[0].strip()
                        if info["cv"] == "-":
                            info["cv"] = parts[1].strip()
                    else:
                        info["circle"] = raw_brand

            # 3. Ambil CV / Voice Actor dari Tabel
            cv_match = re.search(r'<th>\s*(?:声優|キャラクターボイス|ボイス|キャスト)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if cv_match:
                cvs = re.findall(r'<a[^>]*>(.*?)</a>', cv_match.group(1), re.DOTALL)
                clean_cvs = [re.sub(r'<[^>]+>', '', c).strip() for c in cvs if re.sub(r'<[^>]+>', '', c).strip()]
                if clean_cvs:
                    info["cv"] = html.unescape(", ".join(clean_cvs))
                else:
                    raw_cv_td = re.sub(r'<[^>]+>', '', cv_match.group(1)).strip()
                    if raw_cv_td:
                        info["cv"] = html.unescape(raw_cv_td)

            # 4. Fallback CV dari Judul / Deskripsi / Teks Halaman jika belum terisi
            if info["cv"] == "-":
                desc_match = re.search(r'<meta itemprop="description" content="(.*?)">', page_html, re.DOTALL)
                desc_text = html.unescape(desc_match.group(1)) if desc_match else ""
                combined_text = f"{info['title']} {desc_text}"

                cv_patterns = [
                    r'(?:CV|声優|キャラクターボイス|ボイス|キャスト|CV\.|CV：|CV:)\s*[：:\s【\[（(「『]*([^\n\r,、/】\]）)」』\s]{2,30})',
                    r'【(?:CV|声優|ボイス)\s*[：:\s]*([^\n\r,、/】\]）)\s]+)】',
                    r'\((?:CV|声優|ボイス)\s*[：:\s]*([^\n\r,、/】\]）)\s]+)\)',
                ]
                valid_cvs = []
                for pat in cv_patterns:
                    matches = re.findall(pat, combined_text, re.IGNORECASE)
                    for m in matches:
                        clean_m = m.strip()
                        if 1 < len(clean_m) < 30 and not clean_m.startswith("http") and clean_m not in valid_cvs:
                            valid_cvs.append(clean_m)
                if valid_cvs:
                    info["cv"] = ", ".join(valid_cvs)

            # 5. Ambil Genre / Tag dari Tabel atau Meta Keywords DLsite
            genre_match = re.search(r'<th>\s*(?:ジャンル|タグ)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if genre_match:
                g_links = re.findall(r'<a[^>]*>(.*?)</a>', genre_match.group(1), re.DOTALL)
                clean_genres = [re.sub(r'<[^>]+>', '', g).strip() for g in g_links if re.sub(r'<[^>]+>', '', g).strip()]
                if clean_genres:
                    info["genre"] = html.unescape(", ".join(clean_genres))
                else:
                    raw_g = re.sub(r'<[^>]+>', '', genre_match.group(1)).strip()
                    if raw_g:
                        info["genre"] = html.unescape(", ".join([x.strip() for x in raw_g.splitlines() if x.strip()]))

            # Fallback Genre dari meta keywords
            if info["genre"] == "-":
                kw_match = re.search(r'<meta name="keywords" content="(.*?)">', page_html)
                if kw_match:
                    raw_kws = [k.strip() for k in html.unescape(kw_match.group(1)).split(",") if k.strip()]
                    ignore_list = ["DLsite", "同人", "ダウンロード", "R18", "同人誌", "ゲーム", "音声", info.get("circle", "")]
                    filtered_kws = [k for k in raw_kws if k not in ignore_list and not k.startswith("RJ")]
                    if filtered_kws:
                        info["genre"] = ", ".join(filtered_kws[:12])

            # 6. Ambil Rating Usia (年齢指定)
            age_match = re.search(r'<th>\s*(?:年齢指定|レーティング)\s*</th>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
            if age_match:
                clean_age = re.sub(r'<[^>]+>', '', age_match.group(1)).strip()
                if clean_age:
                    info["age_rating"] = html.unescape(clean_age)
            elif "maniax" in url or "r18" in page_html.lower() or "18禁" in page_html:
                info["age_rating"] = "R18"
            else:
                info["age_rating"] = "全年齢"

            if info["title"] and info["title"] != clean_id:
                break
        except Exception:
            continue

    return info
