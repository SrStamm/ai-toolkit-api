from pydantic import BaseModel


class PersonSchema(BaseModel):
    name: str
    age: int
    country: str
