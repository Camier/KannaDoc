from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator

from app.rag.provider_registry import ProviderRegistry


class ModelConfigBase(BaseModel):
    model_name: str
    model_url: str = ""
    api_key: str
    provider: Optional[str] = None
    base_used: List[dict] = []
    system_prompt: str = ""
    temperature: float = 0.7
    max_length: int = 4096
    top_P: float = 0.9
    # Thesis-friendly defaults: allow the runtime (settings) to decide sensible
    # retrieval breadth, instead of accidentally capping recall to a tiny value.
    top_K: int = -1
    # -1 sentinel means "use environment default" (typically no filter for thesis).
    score_threshold: int = -1

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not v or len(v.strip()) < 2:
            raise ValueError("model_name must be at least 2 characters")
        return v.strip()

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        known_providers = ProviderRegistry.get_all_providers()
        if v not in known_providers:
            raise ValueError(
                f"Unknown provider: {v}. Valid providers: {known_providers}"
            )
        return v

    @model_validator(mode="after")
    def validate_or_infer_provider(self) -> "ModelConfigBase":
        """Infer provider from model_name when not explicitly provided.

        Rationale:
        - If the user supplies an explicit provider (e.g. `minimax`), we should not
          reject new/unknown model ids solely because they are not yet listed in
          `providers.yaml`.
        - If provider is omitted, keep the existing safety behavior: unknown model
          ids are rejected because we cannot route them.
        """
        if self.provider is None:
            detected = ProviderRegistry.get_provider_for_model(self.model_name)
            if not detected:
                raise ValueError(
                    f"Unknown model: {self.model_name}. Cannot detect provider."
                )
        return self

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("api_key must be at least 10 characters")
        v = v.strip()
        if v.startswith("sk-") or v.startswith("hf_") or "." in v:
            return v
        if len(v) < 20:
            raise ValueError("api_key appears too short to be valid")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        # -1 is a sentinel value meaning "use provider default"
        if v == -1:
            return v
        if v < 0:
            return 0.0
        if v > 2:
            return 2.0
        return v

    @field_validator("max_length")
    @classmethod
    def validate_max_length(cls, v: int) -> int:
        # -1 is a sentinel value meaning "use provider default"
        if v == -1:
            return v
        # Align with ChatService normalizer: min 1024, max 1048576
        if v < 1024:
            return 1024
        if v > 1048576:
            return 1048576
        return v

    @field_validator("top_P")
    @classmethod
    def validate_top_p(cls, v: float) -> float:
        if v == -1:
            return v
        if v < 0:
            return 0.0
        if v > 1:
            return 1.0
        return v

    @field_validator("top_K")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        if v == -1:
            return v
        if v < 1:
            return 1
        # Align with ChatService normalizer: higher caps are required for thesis (diversification).
        if v > 120:
            return 120
        return v

    @field_validator("score_threshold")
    @classmethod
    def validate_score_threshold(cls, v: int) -> int:
        if v == -1:
            return v
        if v < 0:
            return 0
        # Align with ChatService normalizer: max 20
        if v > 20:
            return 20
        return v


class ModelCreate(ModelConfigBase):
    pass


class ModelUpdate(BaseModel):
    model_name: Optional[str] = None
    model_url: Optional[str] = None
    api_key: Optional[str] = None
    provider: Optional[str] = None
    base_used: Optional[List[dict]] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_length: Optional[int] = None
    top_P: Optional[float] = None
    top_K: Optional[int] = None
    score_threshold: Optional[int] = None

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v.strip()) < 2:
            raise ValueError("model_name must be at least 2 characters")
        return v.strip()

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v.strip()) < 10:
            raise ValueError("api_key must be at least 10 characters")
        return v.strip()

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        known_providers = ProviderRegistry.get_all_providers()
        if v not in known_providers:
            raise ValueError(
                f"Unknown provider: {v}. Valid providers: {known_providers}"
            )
        return v


class SelectedModelResponse(BaseModel):
    status: str
    select_model_config: Optional[dict] = None
    message: Optional[str] = None


class UpdateSelectedModelRequest(BaseModel):
    model_id: str
