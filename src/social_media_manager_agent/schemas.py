from pydantic import BaseModel, Field


class MovieRelease(BaseModel):
    title: str = Field(description="Titolo del film")
    release_date: str = Field(description="Data di uscita del film (YYYY-MM-DD)")
    screening_date: str = Field(description="Data/ora della proiezione in sala (YYYY-MM-DDTHH:MM:SS)")

class CandidateItem(BaseModel):
    title: str = Field(description="Titolo sintetico della notizia o dello spunto")
    summary: str = Field(description="Breve riassunto dello spunto")
    related_movie_title: str | None = Field(
        default=None, description="Titolo del film collegato, se applicabile"
    )

class SelectedItem(BaseModel):
    title: str = Field(description="Titolo sintetico dello spunto selezionato")
    summary: str = Field(description="Breve riassunto")
    reason: str = Field(description="Perché questo spunto è rilevante per promuovere il cinema")
    related_movie_title: str | None = None


class SelectedItems(BaseModel):
    items: list[SelectedItem] = Field( description="Spunti selezionati per generare un post" )


class Post(BaseModel):
    title: str = Field(description="Titolo del post")
    body: str = Field(description="Corpo del post, pronto per la pubblicazione")
    style: str = Field(description="Stile del post (es. Informativo, Celebrativo, Teaser)")
    publish_at: str = Field(description="Data/ora di pubblicazione suggerita (YYYY-MM-DDTHH:MM:SS)")
    related_movie_title: str | None = None
    image_path: str | None = None

    
class CandidateItems(BaseModel):
    items: list[CandidateItem] = Field(description="Spunti di notizia individuati dalla ricerca")

class HistoryEntry(BaseModel):
    title: str = Field(description="Titolo dello spunto pubblicato")
    summary: str = Field(description="Breve riassunto dell'argomento")
    related_movie_title: str | None = None
    created_at: str = Field(description="Data di generazione (YYYY-MM-DD)")