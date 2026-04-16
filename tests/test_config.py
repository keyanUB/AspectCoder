import os
import pytest
from pathlib import Path
from mycoder.config import Config, ModelConfig, load_config

def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
models:
  planner:
    model: claude-opus-4-7
    temperature: 0.7
    max_tokens: 4096
  generator:
    default:
      model: claude-sonnet-4-6
      temperature: 0.2
      max_tokens: 8192
    c:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
    cpp:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
  verifier:
    model: claude-sonnet-4-6
    temperature: 0.0
    max_tokens: 2048
  reviewers:
    functional:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
    security:
      model: claude-sonnet-4-6
      temperature: 0.0
      max_tokens: 2048
    performance:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
  aggregator:
    normal:
      model: claude-haiku-4-5
      temperature: 0.0
      max_tokens: 1024
    failure_report:
      model: claude-sonnet-4-6
      temperature: 0.3
      max_tokens: 2048
api_keys:
  anthropic: test-key
  openai: test-openai-key
""")
    config = load_config(cfg_file)
    assert config.models.planner.model == "claude-opus-4-7"
    assert config.models.planner.temperature == 0.7
    assert config.models.generator["c"].model == "claude-opus-4-7"
    assert config.models.reviewers["security"].model == "claude-sonnet-4-6"
    assert config.models.aggregator["normal"].model == "claude-haiku-4-5"

def test_generator_model_for_language(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
models:
  planner:
    model: claude-opus-4-7
    temperature: 0.7
    max_tokens: 4096
  generator:
    default:
      model: claude-sonnet-4-6
      temperature: 0.2
      max_tokens: 8192
    c:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
    cpp:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
  verifier:
    model: claude-sonnet-4-6
    temperature: 0.0
    max_tokens: 2048
  reviewers:
    functional:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
    security:
      model: claude-sonnet-4-6
      temperature: 0.0
      max_tokens: 2048
    performance:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
  aggregator:
    normal:
      model: claude-haiku-4-5
      temperature: 0.0
      max_tokens: 1024
    failure_report:
      model: claude-sonnet-4-6
      temperature: 0.3
      max_tokens: 2048
api_keys:
  anthropic: test-key
  openai: test-openai-key
""")
    config = load_config(cfg_file)
    assert config.generator_model_for("python").model == "claude-sonnet-4-6"
    assert config.generator_model_for("c").model == "claude-opus-4-7"
    assert config.generator_model_for("cpp").model == "claude-opus-4-7"
    assert config.generator_model_for("javascript").model == "claude-sonnet-4-6"

def test_aggregator_model_normal(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
models:
  planner:
    model: claude-opus-4-7
    temperature: 0.7
    max_tokens: 4096
  generator:
    default:
      model: claude-sonnet-4-6
      temperature: 0.2
      max_tokens: 8192
    c:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
    cpp:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
  verifier:
    model: claude-sonnet-4-6
    temperature: 0.0
    max_tokens: 2048
  reviewers:
    functional:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
    security:
      model: claude-sonnet-4-6
      temperature: 0.0
      max_tokens: 2048
    performance:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
  aggregator:
    normal:
      model: claude-haiku-4-5
      temperature: 0.0
      max_tokens: 1024
    failure_report:
      model: claude-sonnet-4-6
      temperature: 0.3
      max_tokens: 2048
api_keys:
  anthropic: test-key
  openai: test-openai-key
""")
    config = load_config(cfg_file)
    assert config.aggregator_model(failure_report=False).model == "claude-haiku-4-5"
    assert config.aggregator_model(failure_report=True).model == "claude-sonnet-4-6"
