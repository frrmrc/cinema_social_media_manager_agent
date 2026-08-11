from pydantic import BaseModel, Field


class MovieRelease(BaseModel):
    title: str = Field(description="Movie title")
    release_date: str = Field(description="Movie release date (YYYY-MM-DD)")
    screening_date: str = Field(description="Screening date/time in theater (YYYY-MM-DDTHH:MM:SS)")

class CandidateItem(BaseModel):
    title: str = Field(description="Short title of the news item or idea")
    summary: str = Field(description="Brief summary of the idea")
    related_movie_title: str | None = Field(
        default=None, description="Title of the related movie, if applicable"
    )

class SelectedItem(BaseModel):
    title: str = Field(description="Short title of the selected idea")
    summary: str = Field(description="Brief summary")
    reason: str = Field(description="Why this idea is relevant for promoting the cinema")
    related_movie_title: str | None = None


class SelectedItems(BaseModel):
    items: list[SelectedItem] = Field( description="Ideas selected for generating a post" )


class Post(BaseModel):
    title: str = Field(description="Post title")
    body: str = Field(description="Post body, ready for publication")
    style: str = Field(description="Post style (e.g. Informative, Celebratory, Teaser)")
    publish_at: str = Field(description="Suggested publish date/time (YYYY-MM-DDTHH:MM:SS)")
    related_movie_title: str | None = None
    image_path: str | None = None


class CandidateItems(BaseModel):
    items: list[CandidateItem] = Field(description="News ideas found by the search")

class HistoryEntry(BaseModel):
    title: str = Field(description="Title of the published idea")
    summary: str = Field(description="Brief summary of the topic")
    related_movie_title: str | None = None
    created_at: str = Field(description="Generation date (YYYY-MM-DD)")