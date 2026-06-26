"""Build a standards-compliant .epub from a project's chapters — using only the
Python standard library (zipfile/html/uuid), so it adds NO new dependencies.

An EPUB is just a ZIP with a fixed layout. We emit both an EPUB3 nav (`nav.xhtml`)
and an EPUB2 `toc.ncx` so old and new readers (phones, Kindle via conversion,
Apple Books, Calibre, KOReader…) all show a proper table of contents.
"""
from __future__ import annotations

import html
import io
import re
import time
import uuid
import zipfile

CSS = """\
body { font-family: Georgia, 'Times New Roman', serif; line-height: 1.6; margin: 5%; }
h1, h2 { line-height: 1.25; text-align: center; }
h2 { margin-top: 2em; }
p { margin: 0 0 1em; text-indent: 1.4em; text-align: justify; }
p.first { text-indent: 0; }
.title-page { text-align: center; margin-top: 25%; }
.title-page .logline { font-style: italic; margin-top: 1.5em; }
.byline { margin-top: 3em; font-size: .9em; color: #555; }
nav ol { line-height: 2; }
"""


def _paras_html(text: str) -> str:
    blocks = re.split(r"\n\s*\n+", str(text or "").strip())
    out = []
    for i, b in enumerate(blocks):
        b = b.strip()
        if not b:
            continue
        cls = ' class="first"' if i == 0 else ""
        out.append(f"<p{cls}>" + html.escape(b).replace("\n", "<br/>") + "</p>")
    return "\n".join(out) or "<p></p>"


def _xhtml(title: str, body_html: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
        'xml:lang="en" lang="en">\n'
        f"<head><meta charset=\"utf-8\"/><title>{html.escape(title)}</title>"
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
        f"<body>\n{body_html}\n</body>\n</html>\n"
    )


def build_epub(project: dict, chapters: list[dict]) -> bytes:
    title = project.get("title") or "Untitled Novel"
    bible = project.get("bible") or {}
    logline = bible.get("logline") or ""
    book_uuid = f"urn:uuid:{uuid.uuid4()}"
    modified = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Build the ordered list of content documents: optional Chapter 0, then chapters.
    items: list[dict] = []  # {id, href, title, body}
    if project.get("intro"):
        items.append({
            "id": "chap0", "href": "chap0.xhtml", "title": "Chapter 0 — About this world",
            "body": "<h2>Chapter 0 — About this world</h2>\n" + _paras_html(project["intro"]),
        })
    for ch in chapters:
        n = ch["number"]
        ctitle = ch.get("title") or f"Chapter {n}"
        items.append({
            "id": f"chap{n}", "href": f"chap{n}.xhtml", "title": f"Chapter {n}: {ctitle}",
            "body": f"<h2>Chapter {n}<br/>{html.escape(ctitle)}</h2>\n" + _paras_html(ch.get("content", "")),
        })

    # Title page.
    tp_body = (
        '<div class="title-page">\n'
        f"<h1>{html.escape(title)}</h1>\n"
        + (f'<p class="logline">{html.escape(logline)}</p>\n' if logline else "")
        + '<p class="byline">Written locally with the Local Light Novel Writer</p>\n'
        "</div>"
    )
    title_doc = _xhtml(title, tp_body)

    # nav.xhtml (EPUB3)
    nav_lis = "\n".join(
        f'      <li><a href="{it["href"]}">{html.escape(it["title"])}</a></li>' for it in items
    )
    nav_doc = _xhtml(
        "Contents",
        '<nav epub:type="toc" id="toc">\n  <h1>Contents</h1>\n  <ol>\n'
        f"{nav_lis}\n  </ol>\n</nav>",
    )

    # toc.ncx (EPUB2 fallback)
    navpoints = "\n".join(
        f'    <navPoint id="np{i}" playOrder="{i + 1}">\n'
        f"      <navLabel><text>{html.escape(it['title'])}</text></navLabel>\n"
        f'      <content src="{it["href"]}"/>\n    </navPoint>'
        for i, it in enumerate(items)
    )
    ncx = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
        f'  <head><meta name="dtb:uid" content="{book_uuid}"/></head>\n'
        f"  <docTitle><text>{html.escape(title)}</text></docTitle>\n"
        f"  <navMap>\n{navpoints}\n  </navMap>\n</ncx>\n"
    )

    # content.opf
    manifest = [
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '    <item id="css" href="style.css" media-type="text/css"/>',
        '    <item id="titlepage" href="title.xhtml" media-type="application/xhtml+xml"/>',
    ]
    spine = ['    <itemref idref="titlepage"/>']
    for it in items:
        manifest.append(f'    <item id="{it["id"]}" href="{it["href"]}" media-type="application/xhtml+xml"/>')
        spine.append(f'    <itemref idref="{it["id"]}"/>')
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"    <dc:identifier id=\"bookid\">{book_uuid}</dc:identifier>\n"
        f"    <dc:title>{html.escape(title)}</dc:title>\n"
        "    <dc:language>en</dc:language>\n"
        "    <dc:creator>Local Light Novel Writer</dc:creator>\n"
        f'    <meta property="dcterms:modified">{modified}</meta>\n'
        "  </metadata>\n"
        "  <manifest>\n" + "\n".join(manifest) + "\n  </manifest>\n"
        '  <spine toc="ncx">\n' + "\n".join(spine) + "\n  </spine>\n"
        "</package>\n"
    )

    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        "  </rootfiles>\n</container>\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # The mimetype entry MUST be first and stored uncompressed.
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/style.css", CSS)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/nav.xhtml", nav_doc)
        z.writestr("OEBPS/toc.ncx", ncx)
        z.writestr("OEBPS/title.xhtml", title_doc)
        for it in items:
            z.writestr(f"OEBPS/{it['href']}", _xhtml(it["title"], it["body"]))
    return buf.getvalue()
