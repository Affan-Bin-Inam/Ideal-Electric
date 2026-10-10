from pydantic import BaseModel, Field

from api.schemas.catalogue import ORMModel


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: str