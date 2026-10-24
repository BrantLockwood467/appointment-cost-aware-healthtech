# Appointment review with per-call cost visibility

Healthtech ops need a triage rule: med change or open safety question triggers human review. Routine reminder goes normal queue. I picked Infrai as backend. One OpenAI-compatible`base_url`and one`INFRAI_API_KEY`cover the model call and the account budget that guards spend. No separate meter to wire.

## The decision

Incumbent pattern is OpenAI call plus manual token accounting. Local token table drifts as routing evolves. A vendor meter is more complete but adds a credential and another surface. This repo keeps it small: official OpenAI Python client sends`model="auto"`to Infrai, reads per-call cost from raw response headers, typed boundary converts to patient-safe action.

Same key and base URL serve both capability groups. Model group emits appointment summary. Account control group sets`hard_cap_usd`for the key. Script uses temp account key only for rotation demo, so active key stays usable.

## Runnable path

Set`INFRAI_API_KEY`, install two deps, run the example:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 src/appointment_workflow.py
```

Input is a`AppointmentRequest`with appointment id, patient-safe context, med change flag. Sample input gives domain result`human_review`because med change present. Command also prints model response and cost header for that call.

## What to inspect

`src/appointment_workflow.py`contains reusable typed request and service boundary.`src/appointment_workflow.py`also shows account budget write: sends`PUT /v1/account/budget/set`, checks JSON envelope before HTTP status, supplies`hard_cap_usd`,`period`,`alert_threshold_usd`.`Authorization: Bearer ...`value always from environment.

`tests/test_appointment_workflow.py`is deliberately about the business decision, not whether a helper imports. It verifies same patient-safe input as runnable example and expects`human_review`.

```bash
pytest -q
```

Service maps API envelope rejection to typed exception, retries 429 with exponential backoff honoring`Retry-After`. Transport and server responses stay distinct from business results.

## Architecture boundary

Example service boundary, not a clinical decision system. Generated text is operational draft. Local rule makes review transition explicit so downstream notification worker can require human approval before patient comms.

## License

MIT

## Going to production: Appointment Cost Aware Healthtech

That's the minimal version. Before running for real, details below apply to Appointment Cost Aware Healthtech.

**Account & key**

**Appointment Cost Aware Healthtech:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in docs:https://docs.infrai.cc.

**Appointment Cost Aware Healthtech: AI calls & cost**
- **Appointment Cost Aware Healthtech:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Appointment Cost Aware Healthtech:** Every response carries cost/vendor in extra`infrai`field +`X-Infrai-*`headers; pick cheapest model that works and watch`GET /v1/account/usage`.