from fastapi import APIRouter
from app.schemas import ArticleInput, ArticleStructured
from app.services.pipeline import run_pipeline

router = APIRouter()

@router.post("/api/structure", response_model=ArticleStructured)
def structure_endpoint(payload: ArticleInput) -> ArticleStructured:
    return run_pipeline(
        title=payload.title,
        text=payload.text,
        template=payload.options.template,
        generate_wikitext=payload.options.generateWikitext,
    )