from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class Element(BaseModel):
    id: str = Field(..., description="Unique identifier for the element")
    type: Literal[
        "startEvent",
        "endEvent", 
        "task",
        "exclusiveGateway",
        "inclusiveGateway",
        "parallelGateway",
        "intermediateEvent"
    ]
    name: str = Field(..., description="Short, action-based name for tasks")
    eventType: Optional[Literal["none", "message", "timer", "error", "conditional", ""]] = Field(
        None, 
        description="Event type - required for events"
    )
    gatewayDirection: Optional[Literal["diverging", "converging", ""]] = Field(
        None,
        description="Gateway direction - required for gateways"
    )


class Lane(BaseModel):
    id: str = Field(..., description="Unique identifier for the lane")
    name: str = Field(..., description="Sub-actor or role name")
    order: int = Field(..., description="Order of the lane")
    elements: List[Element] = Field(default_factory=list)


class SequenceFlow(BaseModel):
    id: str = Field(..., description="Unique identifier for the sequence flow")
    sourceRef: str = Field(..., description="ID of the source element")
    targetRef: str = Field(..., description="ID of the target element")
    name: Optional[str] = Field(None, description="Condition label for gateway branches")
    conditionExpression: Optional[str] = Field(None, description="Condition for XOR branches")


class Pool(BaseModel):
    id: str = Field(..., description="Unique identifier for the pool")
    name: str = Field(..., description="Actor/department name")
    lanes: List[Lane] = Field(default_factory=list)
    sequenceFlows: List[SequenceFlow] = Field(default_factory=list)


class Process(BaseModel):
    id: str = Field(..., description="Process identifier in snake_case")
    name: str = Field(..., description="Human-readable process name")
    pool: Pool


class BPMN(BaseModel):
    process: Process


class BPMNResponse(BaseModel):
    bpmn: BPMN
    reasoning: str = Field(
        ..., 
        description="Validation report stating if required elements are present"
    )


