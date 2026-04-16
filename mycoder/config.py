from __future__ import annotations
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class ModelConfig:
    model: str
    temperature: float = 0.0
    max_tokens: int = 2048


@dataclass
class ModelsConfig:
    planner: ModelConfig
    generator: dict[str, ModelConfig]      # keys: "default", "c", "cpp", "javascript"
    verifier: ModelConfig
    reviewers: dict[str, ModelConfig]      # keys: "functional", "security", "performance"
    aggregator: dict[str, ModelConfig]     # keys: "normal", "failure_report"


@dataclass
class Config:
    models: ModelsConfig
    api_keys: dict[str, str] = field(default_factory=dict)

    def generator_model_for(self, language: str) -> ModelConfig:
        return self.models.generator.get(language, self.models.generator["default"])

    def aggregator_model(self, *, failure_report: bool) -> ModelConfig:
        key = "failure_report" if failure_report else "normal"
        return self.models.aggregator[key]


def _parse_model_config(data: dict) -> ModelConfig:
    return ModelConfig(
        model=data["model"],
        temperature=data.get("temperature", 0.0),
        max_tokens=data.get("max_tokens", 2048),
    )


def _resolve_env_vars(value: str) -> str:
    if value.startswith("${") and value.endswith("}"):
        var = value[2:-1]
        resolved = os.environ.get(var)
        if resolved is None:
            warnings.warn(
                f"Environment variable '{var}' is not set. API key will be empty.",
                UserWarning,
                stacklevel=3,
            )
            return ""
        return resolved
    return value


def load_config(path: Path | str = "config.yaml") -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)

    m = raw["models"]

    required_sections = ["planner", "generator", "verifier", "reviewers", "aggregator"]
    for section in required_sections:
        if section not in m:
            raise ValueError(
                f"config.yaml is missing required section: models.{section}"
            )

    generator: dict[str, ModelConfig] = {}
    for key, val in m["generator"].items():
        generator[key] = _parse_model_config(val)

    if "default" not in generator:
        raise ValueError(
            "config.yaml is missing required section: models.generator.default"
        )

    reviewers: dict[str, ModelConfig] = {}
    for key, val in m["reviewers"].items():
        reviewers[key] = _parse_model_config(val)

    aggregator: dict[str, ModelConfig] = {}
    for key, val in m["aggregator"].items():
        aggregator[key] = _parse_model_config(val)

    api_keys = {
        k: _resolve_env_vars(str(v))
        for k, v in raw.get("api_keys", {}).items()
    }

    return Config(
        models=ModelsConfig(
            planner=_parse_model_config(m["planner"]),
            generator=generator,
            verifier=_parse_model_config(m["verifier"]),
            reviewers=reviewers,
            aggregator=aggregator,
        ),
        api_keys=api_keys,
    )
