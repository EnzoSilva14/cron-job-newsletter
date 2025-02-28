from pydantic import BaseModel, Field

class NewsLink(BaseModel):
    """Extrai links de notícias de uma página HTML"""
    link: str = Field(description="Link completo da notícia", examples=["https://braziljournal.com/vale-anuncia-dividendo-extraordinario-recompra-e-reduz-capex-mercado-aplaude/"])