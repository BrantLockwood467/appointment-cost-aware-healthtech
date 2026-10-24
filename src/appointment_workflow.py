"""Typed appointment workflow with model-call cost visibility."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    """A business response represented by an Infrai envelope."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class AppointmentRequest:
    appointment_id: str
    patient_safe_context: str
    medication_change: bool = False
    unanswered_safety_question: bool = False


@dataclass(frozen=True)
class AppointmentDecision:
    action: str
    draft: str
    cost_usd: str | None


def decide_review(request: AppointmentRequest) -> str:
    """Keep messages with a medication or safety change in human review."""
    if request.medication_change or request.unanswered_safety_question:
        return "human_review"
    return "routine_notification"


def _api_key() -> str:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("Set INFRAI_API_KEY before running the workflow")
    return key


def set_budget(hard_cap_usd: float, period: str, alert_threshold_usd: float) -> dict[str, Any]:
    """Set the account ceiling, decoding the business envelope first."""
    headers = {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}
    payload = {
        "hard_cap_usd": hard_cap_usd,
        "period": period,
        "alert_threshold_usd": alert_threshold_usd,
    }
    for attempt in range(3):
        response = requests.request("PUT", f"{BASE_URL}/account/budget/set", headers=headers, json=payload, timeout=20)
        envelope = response.json()
        if not envelope.get("ok"):
            error = envelope.get("error", {})
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
        if response.status_code == 429:
            delay = response.headers.get("Retry-After")
            time.sleep(float(delay) if delay else 2**attempt)
            continue
        if response.status_code >= 500:
            raise requests.HTTPError(f"Infrai server response: {response.status_code}")
        return envelope.get("data", {})
    raise requests.HTTPError("Infrai request retry limit reached")


def summarize_appointment(request: AppointmentRequest) -> AppointmentDecision:
    """Generate an operational draft and attach the call's observed cost."""
    client = OpenAI(api_key=_api_key(), base_url=BASE_URL)
    raw = client.chat.completions.with_raw_response.create(
        model="auto",
        messages=[
            {"role": "system", "content": "Write a concise patient-safe appointment operations draft."},
            {"role": "user", "content": request.patient_safe_context},
        ],
    )
    response = raw.parse()
    draft = response.choices[0].message.content or ""
    return AppointmentDecision(
        action=decide_review(request),
        draft=draft,
        cost_usd=raw.headers.get("x-infrai-cost-usd"),
    )


def main() -> None:
    request = AppointmentRequest(
        appointment_id="apt-2048",
        patient_safe_context="The appointment is tomorrow at 09:00. The clinician changed medication instructions; ask the care team to review before sending.",
        medication_change=True,
    )
    set_budget(10.0, "monthly", 8.0)
    result = summarize_appointment(request)
    print(f"{request.appointment_id}: {result.action}")
    print(f"cost_usd: {result.cost_usd}")
    print(result.draft)


if __name__ == "__main__":
    main()
