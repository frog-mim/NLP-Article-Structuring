import re
from app.schemas import ArticleStructured, Infobox, Section
from app.services.renderer import render_wikitext

DATE_RE = r"(?:\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{4})"
HEADING_RE = re.compile(r"^\s*(={2,6})\s*(.*?)\s*\1\s*$", re.MULTILINE)

def run_pipeline(title: str, text: str, template: str, generate_wikitext: bool) -> ArticleStructured:
    article = structure_article(title=title, text=text, template=template)
    if generate_wikitext:
        article.wikitext = render_wikitext(article)
    return article

def _first_paragraph(text: str) -> str:
    for p in re.split(r"\n\s*\n", text.strip()):
        if p.strip():
            return p.strip()
    return next((l.strip() for l in text.splitlines() if l.strip()), "")

def _first_sentence(paragraph: str) -> str:
    m = re.split(r"(?<=[.!?])\s+", paragraph.strip(), maxsplit=1)
    return m[0].strip() if m and m[0].strip() else paragraph.strip()

def _extract_birth_death(lead: str) -> tuple[str | None, str | None]:
    born = None
    died = None

    m = re.search(rf"\(born\s+({DATE_RE})\)", lead, re.IGNORECASE)
    if m:
        born = m.group(1)

    m = re.search(rf"\(died\s+({DATE_RE})\)", lead, re.IGNORECASE)
    if m:
        died = m.group(1)

    if not born:
        m = re.search(rf"\bborn\s+({DATE_RE})\b", lead, re.IGNORECASE)
        if m:
            born = m.group(1)

    if not died:
        m = re.search(rf"\bdied\s+({DATE_RE})\b", lead, re.IGNORECASE)
        if m:
            died = m.group(1)

    return born, died

def _extract_birth_place(lead: str) -> str | None:
    m = re.search(rf"\bborn\s+{DATE_RE}\s+in\s+([^.,;()]+)", lead, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    m = re.search(r"\bborn\s+in\s+([^.,;()]+)", lead, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return None

def _extract_occupation(lead: str) -> str | None:
    # "was an English mathematician and writer, chiefly known for ..."
    m = re.search(r"\b(is|was)\s+(an?|the)\s+([^.;()]+)", lead, re.IGNORECASE)
    if not m:
        return None
    occ = m.group(3).strip()
    occ = re.split(
        r"\bchiefly known for\b|\bknown\s+for\b|\bwho\b|\bwhich\b",
        occ,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    return occ[:160] if occ else None

def _extract_known_for(lead: str) -> str | None:
    # "chiefly known for her work on ..."
    m = re.search(r"\bchiefly known for\s+([^.;]+)", lead, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"\bknown for\s+([^.;]+)", lead, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

def _parse_wiki_headings(text: str) -> tuple[str, list[Section]]:
    """
    If the input contains wiki headings like '== Early life ==',
    return: (lead_text_before_first_heading, sections_from_headings)
    Otherwise return: ("", []).
    """
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return "", []

    first = matches[0]
    lead = text[: first.start()].strip()

    sections: list[Section] = []
    for i, m in enumerate(matches):
        heading = m.group(2).strip() or "Section"
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        sections.append(Section(heading=heading, content=content))

    return lead, sections

def structure_article(title: str, text: str, template: str) -> ArticleStructured:
    text = text.strip()

    # Prefer wiki-heading parsing if headings exist
    heading_lead, heading_sections = _parse_wiki_headings(text)

    if heading_sections:
        lead_para = heading_lead or _first_paragraph(text)
        rest_sections = heading_sections
    else:
        lead_para = _first_paragraph(text)

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        body = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else ""

        rest_sections: list[Section] = []
        if body:
            chunks = re.split(r"\n{2,}", body)
            if len(chunks) >= 3:
                rest_sections = [
                    Section(heading="Early life", content="\n\n".join(chunks[:1]).strip()),
                    Section(heading="Career", content="\n\n".join(chunks[1:-1]).strip()),
                    Section(heading="Legacy", content=chunks[-1].strip()),
                ]
            else:
                rest_sections = [Section(heading="Biography", content=body.strip())]

    lead_sentence = _first_sentence(lead_para)

    birth_date, death_date = _extract_birth_death(lead_sentence)
    birth_place = _extract_birth_place(lead_sentence)
    occupation = _extract_occupation(lead_sentence)
    known_for = _extract_known_for(lead_sentence)

    fields: dict[str, str] = {"name": title}
    if birth_date:
        fields["birth_date"] = birth_date
    if birth_place:
        fields["birth_place"] = birth_place
    if death_date:
        fields["death_date"] = death_date
    if occupation:
        fields["occupation"] = occupation
    if known_for:
        fields["known_for"] = known_for

    return ArticleStructured(
        title=title,
        infobox=Infobox(template=template, fields=fields),
        lead=lead_para,
        sections=rest_sections,
        categories=[],
        references=[],
        wikitext=None,
        debug=None,
    )