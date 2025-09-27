from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime

class Book(BaseModel):
    id: str = Field(alias="_id")
    url: HttpUrl
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    rating: int = Field(ge=0, le=5)
    availability: Optional[str] = None

    price_excl_tax: Optional[str] = None
    price_incl_tax: Optional[str] = None
    tax: Optional[str] = None
    price_incl_tax_num: Optional[float] = None
    price_excl_tax_num: Optional[float] = None
    num_reviews: int = 0

    crawled_at: datetime
    source: str
    content_hash: str

    class Config:
        populate_by_name = True
        from_attributes = True

class Change(BaseModel):
    id: str = Field(alias="_id")
    url: HttpUrl
    changed_at: datetime
    prev_hash: Optional[str] = None
    new_hash: str
    fields_hint: list[str] = []
    class Config:
        populate_by_name = True
        from_attributes = True
