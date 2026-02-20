from typing import List, Literal

from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=64)
    risk_score: int = Field(..., ge=0, le=100)
    decision: Literal["approve", "reject", "approve_with_controls"]
    rationale: str = Field(..., max_length=600)
    # Pydantic v2: use max_length for list constraints
    required_controls: List[str] = Field(default_factory=list, max_length=8)


class StorageRef(BaseModel):
    provider: Literal["pinata"]
    cid: str = Field(default="", max_length=128)


class GovernanceRecord(BaseModel):
    scenario: str = Field(..., min_length=1)
    timestamp_utc: str
    agent_outputs: List[AgentOutput]
    final_risk_score: int = Field(..., ge=0, le=100)
    final_decision: Literal["approve", "reject", "approve_with_controls"]
    conflict_flags: List[str]
    recommended_controls: List[str]
    sha256: str
    sha256_post: str
    storage: StorageRef