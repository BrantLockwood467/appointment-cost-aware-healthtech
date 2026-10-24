import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from appointment_workflow import AppointmentRequest, decide_review


def test_medication_change_requires_human_review() -> None:
    request = AppointmentRequest(
        appointment_id="apt-test",
        patient_safe_context="Medication instructions changed.",
        medication_change=True,
    )

    assert decide_review(request) == "human_review"
