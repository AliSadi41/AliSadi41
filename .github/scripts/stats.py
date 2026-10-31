"""Profil README'si için istatistik ve dil kartlarını (SVG) üretir.

Dış servis kullanmaz; veriyi doğrudan GitHub REST API'sinden çeker.
Kullanım: python stats.py <kullanici_adi> <cikti_klasoru>
GITHUB_TOKEN ortam değişkeni varsa API isteklerinde kullanılır.
"""

import json
import os
import sys
import urllib.request
from html import escape

API = "https://api.github.com"

# GitHub (linguist) dil renkleri
RENKLER = {
    "Python": "#3572A5", "Jupyter Notebook": "#DA5B0B", "PHP": "#4F5D95",
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "CSS": "#663399",
    "HTML": "#e34c26", "Dart": "#00B4AB", "Blade": "#f7523f", "Shell": "#89e051",
    "Java": "#b07219", "C#": "#178600", "C++": "#f34b7d", "C": "#555555",
    "Kotlin": "#A97BFF", "Swift": "#F05138", "Go": "#00ADD8", "SCSS": "#c6538c",
    "Vue": "#41b883", "Dockerfile": "#384d54", "Procfile": "#3B2F63",
}

ARKA = "#0d1117"
KENAR = "#30363d"
BASLIK = "#58a6ff"
METIN = "#c9d1d9"
SOLUK = "#8b949e"
YUKSEKLIK = 180  # iki kart yan yana hizalı dursun diye aynı yükseklik


def istek(yol):
    req = urllib.request.Request(API + yol, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "profil-istatistik",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def veri_topla(kullanici):
    profil = istek(f"/users/{kullanici}")
    repolar = istek(f"/users/{kullanici}/repos?per_page=100&type=owner")
    # Fork'lar ve profil README repo'su dil hesabına girmez
    kendi = [r for r in repolar if not r["fork"] and r["name"].lower() != kullanici.lower()]

    diller = {}
    for r in kendi:
        for dil, bayt in istek(f"/repos/{kullanici}/{r['name']}/languages").items():
            diller[dil] = diller.get(dil, 0) + bayt

    commit = istek(f"/search/commits?q=author:{kullanici}&per_page=1")["total_count"]
    return {
        "commit": commit,
        "repo": profil["public_repos"],
        "yildiz": sum(r["stargazers_count"] for r in repolar),
        "dil_sayisi": len(diller),
        "diller": sorted(diller.items(), key=lambda x: x[1], reverse=True),
    }


def kart(genislik, yukseklik, baslik, icerik):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{genislik}" height="{yukseklik}" '
        f'viewBox="0 0 {genislik} {yukseklik}" role="img" aria-label="{escape(baslik)}">\n'
        f'<style>text{{font-family:"Segoe UI",Ubuntu,"Helvetica Neue",Sans-Serif}}'
        f'.b{{font-size:18px;font-weight:600;fill:{BASLIK}}}'
        f'.e{{font-size:14px;fill:{METIN}}}'
        f'.d{{font-size:14px;font-weight:700;fill:{METIN}}}'
        f'.k{{font-size:12px;fill:{SOLUK}}}</style>\n'
        f'<rect x="0.5" y="0.5" width="{genislik - 1}" height="{yukseklik - 1}" rx="6" '
        f'fill="{ARKA}" stroke="{KENAR}"/>\n'
        f'<text x="25" y="35" class="b">{escape(baslik)}</text>\n'
        f'{icerik}</svg>\n'
    )


def istatistik_karti(v):
    satirlar = [
        ("Toplam Commit", v["commit"]),
        ("Public Repo", v["repo"]),
        ("Kullanılan Dil", v["dil_sayisi"]),
        ("Toplam Yıldız", v["yildiz"]),
    ]
    icerik = ""
    for i, (ad, deger) in enumerate(satirlar):
        y = 72 + i * 28
        icerik += (
            f'<circle cx="31" cy="{y - 5}" r="4" fill="{BASLIK}"/>'
            f'<text x="45" y="{y}" class="e">{ad}:</text>'
            f'<text x="330" y="{y}" class="d" text-anchor="end">{deger}</text>\n'
        )
    return kart(360, YUKSEKLIK, "GitHub İstatistikleri", icerik)


def dil_karti(diller, adet=6):
    toplam = sum(b for _, b in diller) or 1
    # %0.1'in altındaki diller listelenmez
    ust = [(d, b) for d, b in diller if b / toplam >= 0.001][:adet]
    genislik, bar_genislik = 360, 310

    # Yüzdeler tüm diller üzerinden; listede olmayanlar "Diğer" olarak bar'a eklenir
    parcalar = [(d, b / toplam * 100) for d, b in ust]
    kalan = 100 - sum(y for _, y in parcalar)

    icerik = f'<clipPath id="c"><rect x="25" y="52" width="{bar_genislik}" height="8" rx="4"/></clipPath>\n<g clip-path="url(#c)">'
    x = 25.0
    for dil, yuzde in parcalar + ([("Diğer", kalan)] if kalan > 0.05 else []):
        w = bar_genislik * yuzde / 100
        icerik += f'<rect x="{x:.2f}" y="52" width="{w:.2f}" height="8" fill="{RENKLER.get(dil, SOLUK)}"/>'
        x += w
    icerik += "</g>\n"

    for i, (dil, yuzde) in enumerate(parcalar):
        sx = 25 + (i % 2) * 160
        sy = 88 + (i // 2) * 24
        icerik += (
            f'<circle cx="{sx + 5}" cy="{sy - 4}" r="5" fill="{RENKLER.get(dil, SOLUK)}"/>'
            f'<text x="{sx + 16}" y="{sy}" class="k">{escape(dil)} {yuzde:.1f}%</text>\n'
        )
    return kart(genislik, YUKSEKLIK, "En Çok Kullanılan Diller", icerik)


def main():
    kullanici, cikti = sys.argv[1], sys.argv[2]
    v = veri_topla(kullanici)
    os.makedirs(cikti, exist_ok=True)
    with open(os.path.join(cikti, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(istatistik_karti(v))
    with open(os.path.join(cikti, "top-langs.svg"), "w", encoding="utf-8") as f:
        f.write(dil_karti(v["diller"]))
    print(f"commit={v['commit']} repo={v['repo']} yildiz={v['yildiz']} diller={v['diller'][:6]}")


if __name__ == "__main__":
    main()
