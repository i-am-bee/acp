from pydantic import BaseModel, ConfigDict


class AnyModel(BaseModel):
    model_config = ConfigDict(extra="allow")
