from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from openai import OpenAI

from app.schemas import AgentOutput

LOGGER = logging.getLogger(__name__)


DEFAULT_MODEL_NAME = "gpt-4o-mini"


class LLMGenerationError(RuntimeError):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


def _client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def _normalize_agent_dict(agent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept minor variations from the LLM and normalize to AgentOutput schema:
    - agent -> agent_name
    - controls / required_control(s) -> required_controls
    - score / risk -> risk_score
    """
    if not isinstance(agent, dict):
        return {}

    a = dict(agent)

    # agent_name
    if "agent_name" not in a:
        if "agent" in a:
            a["agent_name"] = a.get("agent")
        elif "name" in a:
            a["agent_name"] = a.get("name")

    # risk_score
    if "risk_score" not in a:
        for k in ("risk", "score", "riskScore", "risk_score_value"):
            if k in a:
                a["risk_score"] = a.get(k)
                break

    # required_controls
    if "required_controls" not in a:
        for k in ("controls", "required_control", "required_controls_list"):
            if k in a:
                a["required_controls"] = a.get(k)
                break

    # Ensure list type for required_controls
    rc = a.get("required_controls")
    if rc is None:
        a["required_controls"] = []
    elif isinstance(rc, str):
        a["required_controls"] = [rc]
    elif not isinstance(rc, list):
        a["required_controls"] = []

    return a


def generate_agent_outputs_via_openai(scenario: str, api_key: str) -> List[AgentOutput]:
    client = _client(api_key)

    model_name = os.getenv("SENTINEL_OPENAI_MODEL", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME

    system_prompt = (
        "You are Sentinel, a multi-agent AI governance orchestrator.\n"
        "Return ONLY valid JSON (no markdown, no commentary).\n"
        "The JSON MUST be exactly:\n"
        "{\n"
        '  "agent_outputs": [\n'
        "    {\n"
        '      "agent_name": "Security" | "Compliance" | "Ops",\n'
        '      "risk_score": integer 0-100,\n'
        '      "decision": "approve" | "reject" | "approve_with_controls",\n'
        '      "rationale": string <= 600 chars,\n'
        '      "required_controls": array of strings, length <= 8\n'
        "    }, ... exactly 3 items total\n"
        "  ]\n"
        "}\n"
        "Use agent_name (NOT agent). Use risk_score (NOT risk). Use required_controls (NOT controls)."
    )

    user_prompt = (
        f"Scenario:\n{scenario}\n\n"
        "Decide as Security, Compliance, and Ops.\n"
        "Return ONLY JSON in the specified format."
    )

    # Prefer strict JSON output if supported by the model+SDK; fallback if not accepted.
    try:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
        except TypeError:
            # If response_format is not supported for this route/model/sdk combo
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("OpenAI generation failed: %s", exc)
        raise LLMGenerationError("openai_request_failed", code="request") from exc

    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError) as exc:
        LOGGER.warning("OpenAI response missing content: %s", exc)
        raise LLMGenerationError("empty_response", code="parse") from exc

    if not content:
        raise LLMGenerationError("empty_response", code="parse")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        LOGGER.warning("OpenAI JSON parse error: %s | content=%r", exc, content[:500])
        raise LLMGenerationError("json_decode", code="parse") from exc

    outputs = parsed.get("agent_outputs")
    if not isinstance(outputs, list):
        raise LLMGenerationError("missing_agent_outputs", code="parse")

    agent_objects: List[AgentOutput] = []
    try:
        for agent in outputs:
            norm = _normalize_agent_dict(agent)
            agent_objects.append(AgentOutput(**norm))
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("OpenAI payload validation failed: %s | parsed=%r", exc, parsed)
        raise LLMGenerationError("validation", code="parse") from exc

    required_names = {"Security", "Compliance", "Ops"}
    received_names = {a.agent_name for a in agent_objects}
    if received_names != required_names:
        raise LLMGenerationError("invalid_agents", code="parse")

    return agent_objects