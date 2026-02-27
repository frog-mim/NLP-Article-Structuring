from app.schemas import ArticleStructured

def render_wikitext(article: ArticleStructured) -> str:
    lines: list[str] = []

    # Infobox
    ib = article.infobox
    lines.append(f"{{{{{ib.template}")
    for k, v in ib.fields.items():
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        lines.append(f"| {k} = {s}")
    lines.append("}}")
    lines.append("")

    # Lead
    if article.lead.strip():
        lines.append(article.lead.strip())
        lines.append("")

    # Sections
    for sec in article.sections:
        heading = sec.heading.strip() or "Section"
        content = sec.content.strip()
        lines.append(f"== {heading} ==")
        if content:
            lines.append(content)
        lines.append("")

    # Categories
    for cat in article.categories:
        c = cat.strip()
        if c:
            lines.append(f"[[Category:{c}]]")

    return "\n".join(lines).strip() + "\n"