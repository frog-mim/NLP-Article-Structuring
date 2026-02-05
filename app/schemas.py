from pydantic import BaseModel

class ArticleInput(BaseModel):
    title: str
    text: str
