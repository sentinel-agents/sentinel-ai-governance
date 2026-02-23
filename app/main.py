import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List

import openai
import openai as openai_package
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.llm_openai import LLMGenerationError, generate_agent_outputs_via_openai
from app.schemas import AgentOutput, GovernanceRecord, StorageRef
from app.storage_pinata import upload_json

import os
from dotenv import load_dotenv
from app.crypto_sign import load_or_create_keypair, public_key_b64, sign_hash, verify_signature

# Load environment variables from .env file
load_dotenv()

print("OPENAI LOADED:", bool(os.getenv("OPENAI_API_KEY")))
print("PINATA LOADED:", bool(os.getenv("PINATA_JWT")))


class RunSentinelRequest(BaseModel):
    scenario: str = Field(..., min_length=1)


def canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


LOGGER = logging.getLogger("sentinel.main")
OPENAI_LIBRARY_VERSION = getattr(openai_package, "__version__", "unknown")

app = FastAPI(title="Sentinel")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page_title": "Sentinel – AI Governance Layer",
        },
    )


@app.get("/health")
def health():
    version_value = getattr(openai_package, "__version__", None)
    if not version_value:
        version_module = getattr(openai_package, "version", None)
        version_value = getattr(version_module, "__version__", None) or getattr(version_module, "VERSION", None) or version_module
    if not isinstance(version_value, str):
        version_value = str(version_value)
    return {
        "ok": True,
        "mode": os.getenv("SENTINEL_MODE", "auto"),
        "openai_key_present": bool(os.getenv("OPENAI_API_KEY")),
        "pinata_present": bool(os.getenv("PINATA_JWT")),
        "openai_version": version_value,
    }


KEYWORD_WEIGHTS: Dict[str, Dict[str, int]] = {
    "security": {
        "supply chain": 25,
        "autonomy": 15,
        "critical": 20,
        "prod": 10,
        "finance": 15,
        "keys": 10,
    },
    "compliance": {
        "pii": 25,
        "gdpr": 25,
        "audit": 15,
        "policy": 10,
        "reg": 10,
        "iso": 10,
    },
    "ops": {
        "deployment": 20,
        "release": 18,
        "rollback": 15,
        "latency": 12,
        "availability": 15,
        "throughput": 10,
    },
}

BASELINES = {
    "security": 50,
    "compliance": 40,
    "ops": 35,
}


def score_agent(agent: str, scenario: str) -> int:
    tokens = scenario.lower()
    weights = KEYWORD_WEIGHTS[agent]
    score = BASELINES[agent]
    for keyword, weight in weights.items():
        if keyword in tokens:
            score += weight
    return max(0, min(100, score))


def decision_from_score(score: int) -> str:
    if score >= 75:
        return "reject"
    if score >= 50:
        return "approve_with_controls"
    return "approve"


def simulate_agents(scenario: str) -> List[AgentOutput]:
    security_score = score_agent("security", scenario)
    compliance_score = score_agent("compliance", scenario)
    ops_score = score_agent("ops", scenario)

    agents = [
        AgentOutput(
            agent_name="Security",
            risk_score=security_score,
            decision=decision_from_score(security_score),
            rationale="Security agent evaluated threat surfaces and privilege boundaries across the proposed workflow.",
            required_controls=[
                "Zero-trust policy enforcement",
                "Continuous SBOM attestation",
            ]
            if security_score >= 50
            else ["Runtime anomaly detection"],
        ),
        AgentOutput(
            agent_name="Compliance",
            risk_score=compliance_score,
            decision=decision_from_score(compliance_score),
            rationale="Compliance agent mapped obligations to ISO 27001 Annex A and regulatory guidance.",
            required_controls=[
                "Quarterly policy attestation",
                "Data residency logging",
            ]
            if compliance_score >= 50 or "pii" in scenario.lower()
            else ["Access review automation"],
        ),
        AgentOutput(
            agent_name="Ops",
            risk_score=ops_score,
            decision=decision_from_score(ops_score),
            rationale="Ops agent validated deployment safety nets, rollback readiness, and observability depth.",
            required_controls=[
                "Canary deployments",
                "Error budget telemetry",
            ]
            if ops_score >= 50
            else ["Blue/green readiness checklist"],
        ),
    ]

    return agents



def resolve_mode(api_key_present: bool, sentinel_mode: str) -> tuple[bool, str]:
    if sentinel_mode == "openai":
        return True, "OPENAI"
    if sentinel_mode == "mock":
        return False, "MOCK"
    if api_key_present:
        return True, "AUTO->OPENAI"
    return False, "AUTO->MOCK"


@app.post("/run", response_model=GovernanceRecord)
def run_sentinel(payload: RunSentinelRequest, response: Response):
    scenario_text = payload.scenario.strip()
    timestamp = datetime.now(timezone.utc).isoformat()

    conflict_flags: List[str] = []

    sentinel_mode_raw = os.getenv("SENTINEL_MODE", "auto").strip().lower()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    use_llm, desired_label = resolve_mode(bool(api_key), sentinel_mode_raw)
    actual_mode_label = desired_label
    fallback_triggered = False
    openai_error_type = ""
    openai_error_msg = ""

    if sentinel_mode_raw == "openai" and not api_key:
        openai_error_type = "missing_api_key"
        openai_error_msg = "OPENAI_API_KEY not configured"
        LOGGER.error("OpenAI mode requested but OPENAI_API_KEY is missing")
        raise HTTPException(
            status_code=502,
            detail={
                "error": openai_error_type,
                "message": "OPENAI_API_KEY not configured",
            },
        )

    agent_outputs: List[AgentOutput] | None = None

    if use_llm and api_key:
        try:
            agent_outputs = generate_agent_outputs_via_openai(scenario_text, api_key)
            actual_mode_label = desired_label
        except LLMGenerationError as exc:
            openai_error_type = exc.code or "LLMGenerationError"
            openai_error_msg = str(exc) or "OpenAI generation error"
            LOGGER.exception("OpenAI LLMGenerationError: %s", exc)
            if sentinel_mode_raw == "openai":
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": openai_error_type,
                        "message": "OpenAI generation failed; see server logs.",
                    },
                )
            fallback_triggered = True
            conflict_flags.append("llm_fallback_mock")
            if exc.code == "parse":
                conflict_flags.append("llm_parse_error")
            actual_mode_label = f"{desired_label}->MOCK"
        except Exception as exc:  # noqa: BLE001
            openai_error_type = exc.__class__.__name__
            openai_error_msg = str(exc) or "Unexpected OpenAI failure"
            LOGGER.exception("Unexpected OpenAI failure: %s", exc)
            if sentinel_mode_raw == "openai":
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": openai_error_type,
                        "message": "OpenAI generation failed; see server logs.",
                    },
                )
            fallback_triggered = True
            conflict_flags.append("llm_fallback_mock")
            actual_mode_label = f"{desired_label}->MOCK"
    elif use_llm and not api_key:
        openai_error_type = "missing_api_key"
        openai_error_msg = "OPENAI_API_KEY not configured"
        fallback_triggered = True
        conflict_flags.append("llm_fallback_mock")
        actual_mode_label = f"{desired_label}->MOCK"

    if agent_outputs is None:
        agent_outputs = simulate_agents(scenario_text)

    avg_score = sum(agent.risk_score for agent in agent_outputs) // len(agent_outputs)

    if any(agent.decision == "reject" for agent in agent_outputs):
        final_decision = "reject"
    elif any(agent.decision == "approve_with_controls" for agent in agent_outputs):
        final_decision = "approve_with_controls"
    else:
        final_decision = "approve"

    agent_priority = ["Security", "Compliance", "Ops"]
    recommended_controls: List[str] = []
    seen_controls = set()
    for priority_agent in agent_priority:
        for agent in agent_outputs:
            if agent.agent_name != priority_agent:
                continue
            for control in agent.required_controls:
                if control in seen_controls:
                    continue
                seen_controls.add(control)
                recommended_controls.append(control)

    if len({agent.decision for agent in agent_outputs}) > 1:
        conflict_flags.append("decision_disagreement")

    storage = StorageRef(provider="pinata", cid="")

    record_dict = {
        "scenario": scenario_text,
        "timestamp_utc": timestamp,
        "agent_outputs": [agent.model_dump() for agent in agent_outputs],
        "final_risk_score": avg_score,
        "final_decision": final_decision,
        "conflict_flags": conflict_flags,
        "recommended_controls": recommended_controls,
        "sha256": "",
        "sha256_post": "",
        "storage": storage.model_dump(),
    }

    canonical_pre = canonical_bytes(record_dict)
    record_dict["sha256"] = hashlib.sha256(canonical_pre).hexdigest()

    storage_token = os.getenv("PINATA_JWT", "").strip()
    cid = ""
    if storage_token:
        cid = upload_json(canonical_pre, storage_token)
        if cid:
            record_dict["storage"]["cid"] = cid
        else:
            record_dict["conflict_flags"].append("storage_upload_failed")
    else:
        record_dict["conflict_flags"].append("storage_token_missing")

    canonical_post = canonical_bytes(record_dict)
    record_dict["sha256_post"] = hashlib.sha256(canonical_post).hexdigest()

    # --- Milestone 1B: Ed25519 signature over sha256_post ---
    try:
        priv_bytes, pub_bytes = load_or_create_keypair()
        signed_hash = record_dict["sha256_post"]
        record_dict["signature_alg"] = "ed25519"
        record_dict["signed_hash"] = signed_hash
        record_dict["public_key"] = public_key_b64(pub_bytes)
        record_dict["signature"] = sign_hash(priv_bytes, signed_hash)

        # Optional: add conflict flag if verification fails
        if "verify_signature" in globals():
            if not verify_signature(pub_bytes, signed_hash, record_dict["signature"]):
                record_dict["conflict_flags"].append("signature_verify_failed")
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Signature generation failed: %s", exc)
        record_dict["conflict_flags"].append("signature_generation_failed")
        # If schema requires signature fields, we still must set them (non-empty ideally).
        # But better: re-raise to catch bug early during milestone.
        raise

    fallback_header = "1" if (fallback_triggered or ("MOCK" in actual_mode_label)) else "0"
    response.headers["x-sentinel-mode"] = actual_mode_label
    response.headers["x-sentinel-fallback"] = fallback_header
    response.headers["x-sentinel-openai-error-type"] = openai_error_type
    response.headers["x-sentinel-openai-error"] = openai_error_msg

    return GovernanceRecord(**record_dict)

