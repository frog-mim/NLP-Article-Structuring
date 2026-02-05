from fastapi import APIRouter
from app.schemas import ArticleInput
from app.services.preprocessing import preprocess
from app.services.classification import classify
from app.services.ner import run_ner
from app.services.information_extraction import extract_info
from app.services.combine import combine_results

router = APIRouter()

@router.post("/process")
def process_article(article: ArticleInput):

    clean_text = preprocess(article.text)

    label = classify(clean_text)

    entities = run_ner(clean_text)

    facts = extract_info(clean_text)

    structured = combine_results(
        article.title,
        label,
        entities,
        facts
    )

    return structured
