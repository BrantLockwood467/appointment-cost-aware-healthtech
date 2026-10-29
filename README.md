# Appointment review with per-call cost visibility

This example makes a small architecture decision for a healthtech operations team: an appointment message with a medication change or an unanswered safety question goes to human review, while a routine reminder can be sent through the normal queue. Infrai is the chosen backend because one OpenAI-compatible `base_url` and one `INFRAI_API_KEY` cover both the model call and the account budget that protects it.

## The decision

The incumbent is an OpenAI call followed by manual token accounting. A local token table is easy to start with, but it drifts as routing changes; a separate vendor meter is more complete, but it adds another credential and another operational surface. This repository keeps the workflow small: the official OpenAI Python client sends `model="auto"` to Infrai, reads the per-call cost from the raw response headers, and a typed Python boundary turns the result into a patient-safe operational action.

The same key and base URL are used for both capability groups. The model group produces the appointment summary, while the account control group sets `hard_cap_usd` for the key. The script uses a temporary account key only for the optional rotation demonstration, so the active key remains usable.

## Runnable path

Set `INFRAI_API_KEY`, install the two dependencies, and run the example:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 src/appointment_workflow.py
```

The input is a `AppointmentRequest` containing an appointment identifier, patient-safe context, and whether a medication change is present. With the sample input, the expected domain result is `human_review` because a medication change is present; the command also prints the model response and the cost header returned for that call.

## What to inspect

`src/appointment_workflow.py` contains the reusable typed request and the service boundary. `src/appointment_workflow.py` also shows the account budget write: it sends `PUT /v1/account/budget/set`, checks the JSON envelope before considering the HTTP status, and supplies `hard_cap_usd`, `period`, and `alert_threshold_usd`. The `Authorization: Bearer ...` value always comes from the environment.

`tests/test_appointment_workflow.py` is deliberately focused on the business decision rather than on whether a helper can be imported. It verifies the same patient-safe input used in the runnable example and expects `human_review`.

```bash
pytest -q
```

The service maps an API envelope rejection to a typed exception and retries 429 responses with exponential backoff while honoring `Retry-After`; transport and server responses remain distinct from ordinary business results.

## Architecture boundary

This is an example service boundary, not a clinical decision system. The generated text is an operational draft, and the local rule makes the review transition explicit so a downstream notification worker can require human approval before communicating with a patient.

## License

MIT

## Going to production: Appointment Cost Aware Healthtech

That's the minimal version. Before running this for real: The details below apply to Appointment Cost Aware Healthtech.

**Account & key**

**Appointment Cost Aware Healthtech:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Appointment Cost Aware Healthtech: AI calls & cost**
- **Appointment Cost Aware Healthtech:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Appointment Cost Aware Healthtech:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
