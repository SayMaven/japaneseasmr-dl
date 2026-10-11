import html
import json
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


def check_url_accessible(url, referer="https://japaneseasmr.com", user_agent=USER_AGENT, timeout=3.5):
    """Mengecek apakah URL gambar/audio dapat diakses (HTTP 200/206)."""
    headers = {"User-Agent": user_agent, "Range": "bytes=0-10"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status in (200, 206):
                return True
    except Exception:
        pass
    return False


def resolve_best_cover_url(rj_id, dlsite_cover=None):
    """
    Menentukan URL gambar cover terbaik dengan alur fallback:
    1. pic.weeabo0.xyz (JapaneseASMR) jika tersedia.
    2. DLsite HD Cover (og:image / modpub) jika tersedia.
    3. asmr.one cover art (mainCoverUrl).
    4. Fallback default ke pic.weeabo0.xyz.
    """
    clean_id = rj_id.strip().upper()
    weeabo_url = f"https://pic.weeabo0.xyz/{clean_id}_img_main.jpg"
    if check_url_accessible(weeabo_url, referer="https://japaneseasmr.com"):
        return weeabo_url

    if dlsite_cover and check_url_accessible(dlsite_cover, referer="https://www.dlsite.com"):
        return dlsite_cover

    # Fallback ke asmr.one
    num_id = re.sub(r'^[A-Za-z]+', '', clean_id)
    if num_id:
        asmrone_cover = f"https://api.asmr.one/api/cover/{num_id}.jpg?type=main"
        if check_url_accessible(asmrone_cover, referer="https://asmr.one/"):
            return asmrone_cover

    return weeabo_url


def enrich_metadata_from_asmrone(rj_id, info):
    """
    Fallback untuk karya yang terkena geo-blocking DLsite atau yang tabel outlinenya tidak ter-render.
    Mengambil CV/Seiyuu dan Genre/Tag dari asmr.one API yang tidak dibatasi region.
    """
    clean_id = rj_id.strip().upper()
    num_id = re.sub(r'^[A-Za-z]+', '', clean_id)
    if not num_id:
        return info

    url = f"https://api.asmr.one/api/work/{num_id}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://asmr.one/",
            "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=4.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

            # 1. CV / Seiyuu
            if info.get("cv") == "-" and data.get("vas"):
                vas = [v.get("name", "").strip() for v in data.get("vas", []) if v.get("name")]
                if vas:
                    info["cv"] = ", ".join(vas)

            # 2. Genre / Tags (utamakan tag Jepang melalui i18n jika ada agar seragam dengan DLsite)
            if info.get("genre") == "-" and data.get("tags"):
                tags = []
                for t in data.get("tags", []):
                    i18n_ja = t.get("i18n", {}).get("ja-jp", {}).get("name") if isinstance(t.get("i18n"), dict) else None
                    name = i18n_ja or t.get("name")
                    if name and name.strip() and name.strip() not in tags:
                        tags.append(name.strip())
                if tags:
                    info["genre"] = ", ".join(tags)

            # 3. Circle / Maker jika masih '-'
            if info.get("circle") == "-":
                c = data.get("circle")
                if isinstance(c, dict) and c.get("name"):
                    info["circle"] = c["name"].strip()
                elif data.get("name"):
                    info["circle"] = str(data["name"]).strip()

            # 4. Age Rating jika masih '-'
            if info.get("age_rating") == "-":
                age = data.get("age_category_string")
                if age:
                    info["age_rating"] = str(age).strip()
    except Exception:
        pass

    return info


def fetch_dlsite_metadata(rj_id):
    """Mengambil metadata karya (Judul, CV, Circle, Genre, Rating, Cover HD) langsung dari DLsite resmi."""
    clean_id = rj_id.strip().upper()
    info = {
        "title": clean_id,
        "cv": "-",
        "circle": "-",
        "genre": "-",
        "age_rating": "-",
        "cover_url": f"https://pic.weeabo0.xyz/{clean_id}_img_main.jpg",
        "dlsite_cover_url": None,
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

            # 0. Ambil Cover HD Resmi dari og:image DLsite
            og_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']', page_html, re.IGNORECASE)
            if not og_match:
                og_match = re.search(r'<meta\s+name=["\']twitter:image["\']\s+content=["\'](.*?)["\']', page_html, re.IGNORECASE)
            if og_match:
                info["dlsite_cover_url"] = html.unescape(og_match.group(1).strip())

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

    # 7. Fallback Enrichment via asmr.one jika CV atau Genre masih kosong '-'
    # (Penyebab utama: karya terkena geo-blocking DLsite sehingga tabel detail tidak dikirim oleh server DLsite)
    if info.get("cv") == "-" or info.get("genre") == "-" or info.get("circle") == "-":
        info = enrich_metadata_from_asmrone(clean_id, info)

    # Resolusi cover terbaik (Weeabo0 -> DLsite HD -> asmr.one)
    info["cover_url"] = resolve_best_cover_url(clean_id, info.get("dlsite_cover_url"))
    return info

