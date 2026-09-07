from __future__ import annotations

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import mwparserfromhell


def normalize_template_name(template_name: str) -> str:
    name = re.sub(r"<!--.*?-->", " ", template_name, flags=re.DOTALL)
    name = re.sub(r"<[^>]+>", " ", name)
    name = name.strip().replace("_", " ")
    name = re.sub(r"\s+", " ", name)
    if not name.lower().startswith("infobox"):
        return ""
    parts = name.split()
    return " ".join(part.capitalize() if part.lower() != "of" else part.lower() for part in parts)


def detect_infobox_label(wikitext: str) -> str | None:
    result = extract_infobox_template(wikitext)
    return result[0] if result else None


def extract_infobox_template(wikitext: str) -> tuple[str, mwparserfromhell.nodes.Template] | None:
    try:
        wikicode = mwparserfromhell.parse(wikitext)
    except Exception:
        return None

    for template in wikicode.filter_templates(recursive=True):
        label = normalize_template_name(str(template.name))
        if label:
            return label, template
    return None


def normalize_parameter_name(parameter_name: str) -> str:
    name = re.sub(r"<!--.*?-->", " ", parameter_name, flags=re.DOTALL)
    name = re.sub(r"<[^>]+>", " ", name)
    name = name.strip().replace(" ", "_")
    name = re.sub(r"_+", "_", name)
    return name.strip("_").lower()


def clean_infobox_value(value: str) -> str:
    value = re.sub(r"<ref\b[^>/]*>.*?</ref>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<ref\b[^/]*/\s*>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\{\{\s*(?:birth date(?: and age)?|death date(?: and age)?)\s*\|\s*"
        r"(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})(?:\|[^{}]*)?\}\}",
        r"\1-\2-\3",
        value,
        flags=re.IGNORECASE,
    )

    try:
        cleaned = mwparserfromhell.parse(value).strip_code(normalize=True, collapse=True)
    except Exception:
        cleaned = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", value)
        cleaned = re.sub(r"\{\{.*?\}\}", " ", cleaned, flags=re.DOTALL)

    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_infobox_fields(template: mwparserfromhell.nodes.Template) -> dict[str, str]:
    fields: dict[str, str] = {}
    for parameter in template.params:
        raw_name = str(parameter.name)
        field_name = normalize_parameter_name(raw_name)
        if not field_name or field_name.isdigit():
            continue

        field_value = clean_infobox_value(str(parameter.value))
        if not field_value:
            continue

        fields[field_name] = field_value
    return fields


def clean_wikitext(wikitext: str) -> str:
    try:
        wikicode = mwparserfromhell.parse(wikitext)
        cleaned = wikicode.strip_code(normalize=True, collapse=True)
    except Exception:
        cleaned = re.sub(r"\{\{.*?\}\}", " ", wikitext, flags=re.DOTALL)
        cleaned = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_text_element(element: ET.Element, name: str, namespace: dict[str, str]) -> str:
    if namespace:
        namespaced = element.findtext(f"mw:{name}", default="", namespaces=namespace)
        if namespaced:
            return namespaced
    return element.findtext(name, default="")


def iter_pages(xml_path: Path):
    if not xml_path.exists():
        raise FileNotFoundError(
            f"Input XML not found: {xml_path}. "
            "Provide a Wikipedia XML dump, or first create this file with "
            "`python app/ml/filter_people_dump.py --xml data/enwiki.xml --out data/people_only.xml`."
        )

    context = ET.iterparse(xml_path, events=("start", "end"))
    _, root = next(context)
    namespace_uri = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""
    namespace = {"mw": namespace_uri} if namespace_uri else {}

    for event, elem in context:
        page_tag = f"{{{namespace_uri}}}page" if namespace_uri else "page"
        if event == "end" and elem.tag == page_tag:
            yield elem, namespace
            elem.clear()
            root.clear()


def build_dataset(xml_path: Path, out_path: Path, limit: int | None = None) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["title", "text", "label", "infobox_fields"])

        for page, namespace in iter_pages(xml_path):
            title = extract_text_element(page, "title", namespace).strip()
            revision = page.find("mw:revision", namespace) if namespace else page.find("revision")
            if revision is None:
                continue
            text = extract_text_element(revision, "text", namespace)
            if not title or not text or text.lstrip().upper().startswith("#REDIRECT"):
                continue

            infobox = extract_infobox_template(text)
            if not infobox:
                continue
            label, template = infobox
            infobox_fields = extract_infobox_fields(template)

            cleaned_text = clean_wikitext(text)
            if not cleaned_text:
                continue

            writer.writerow(
                [
                    title,
                    cleaned_text,
                    label,
                    json.dumps(infobox_fields, ensure_ascii=False, sort_keys=True),
                ]
            )
            written += 1
            if limit is not None and written >= limit:
                break

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a training dataset from Wikipedia XML.")
    parser.add_argument("--xml", required=True, help="Path to Wikipedia XML export or dump.")
    parser.add_argument("--out", required=True, help="Path to output CSV file.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum labeled articles to export.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = build_dataset(Path(args.xml), Path(args.out), args.limit)
    print(f"Wrote {count} labeled articles to {args.out}")


if __name__ == "__main__":
    main()
