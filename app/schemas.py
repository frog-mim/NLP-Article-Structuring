from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class StructureOptions(BaseModel):
    generateWikitext: bool = True
    template: str = "Infobox person"
    language: Optional[str] = "en"
    returnDebug: bool = False
    extra: Dict[str, Any] = Field(default_factory=dict)


class ArticleInput(BaseModel):
    title: str
    text: str
    options: StructureOptions = Field(default_factory=StructureOptions)

class Infobox(BaseModel):
    template: str = "Infobox person"
    fields: Dict[str, Any] = Field(default_factory=dict)


class Section(BaseModel):
    heading: str
    content: str


class ArticleStructured(BaseModel):
    title: str
    infobox: Infobox
    lead: str
    sections: List[Section] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    references: List[Dict[str, Any]] = Field(default_factory=list)

    wikitext: Optional[str] = None