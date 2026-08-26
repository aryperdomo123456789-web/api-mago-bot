from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OnboardingSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int = Field(gt=0)
    provider_type: str = Field(default="evolution", min_length=3, max_length=32)
    recipient: str = Field(default="5511999999999", min_length=8, max_length=32)
    body: str = Field(default="Mensagem de teste do Mago Bot", min_length=1, max_length=4096)


class OnboardingStep(BaseModel):
    key: str
    label: str
    status: str
    action: str | None = None
