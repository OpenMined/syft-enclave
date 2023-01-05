from typing import Any, List, Union

from pydantic import BaseModel


class InputValues(BaseModel):
    type: str
    value: Union[int, float, str, bytes]
    
class InputPerformOpertation(BaseModel):
    inputs: List[InputValues] 
    args: List[Any] = []
    kwargs: dict = {}

class InputPublishRequest(BaseModel):
    dataset_id: str
    sigma: float

class InputPublishRequestCurrentBudget(BaseModel):
    publish_request_id: str
    current_budget: int
    
class InputPublishRequestApproval(BaseModel):
    publish_request_id: str
    budget_deducted: bool
