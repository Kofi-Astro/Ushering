"""Loads the site's editable content — services, gallery, testimonials, FAQ
and site-wide settings — straight out of the `content/` folder in this repo.

These are plain Markdown files with YAML front matter (parsed with
python-frontmatter) plus one settings.json file. They're the same files the
content-admin (Decap CMS, at /content-admin) edits and commits back to this
repo — this module is simply the Python-side reader for them, replacing what
used to be Eleventy's collections API.
"""

import json
from pathlib import Path

import frontmatter
import markdown as md

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def _load_collection(subdir: str) -> list[dict]:
    folder = CONTENT_DIR / subdir
    items = []
    if not folder.exists():
        return items
    for path in sorted(folder.glob("*.md")):
        post = frontmatter.load(path)
        data = dict(post.metadata)
        body = post.content.strip()
        data["body_html"] = md.markdown(body) if body else ""
        items.append(data)
    items.sort(key=lambda d: d.get("order", 0))
    return items


def get_services() -> list[dict]:
    return _load_collection("services")


def get_testimonials() -> list[dict]:
    return _load_collection("testimonials")


def get_gallery_items() -> list[dict]:
    return _load_collection("gallery")


def get_faqs() -> list[dict]:
    return _load_collection("faq")


def get_site_settings() -> dict:
    # Not cached: this is a tiny file and re-reading it means a content-admin
    # save is reflected on the very next request, no restart needed.
    settings_path = CONTENT_DIR / "settings.json"
    return json.loads(settings_path.read_text())
