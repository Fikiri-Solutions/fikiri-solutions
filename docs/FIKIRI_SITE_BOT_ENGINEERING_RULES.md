# Fikiri Engineering Rules for New Features

## Working Standard

Build small, production-minded features with clear boundaries, efficient tests, and reusable code. Avoid overengineering, but do not ship fragile logic that will collapse once the feature grows.

The default pattern is:

1. Define the smallest useful version.
2. Touch the fewest files possible.
3. Keep business logic separate from routes and UI.
4. Add focused tests that catch realistic regressions.
5. Avoid large rewrites unless the existing design is blocking correctness.

## Cursor Agent Rules

When using Cursor, keep the prompt scoped and token-efficient.

Every agent prompt should include:

```text
Goal:
Files allowed:
Files not allowed:
Implementation rules:
Testing required:
Acceptance criteria:
Output required:
```

Cursor should not freely explore the whole repo unless explicitly asked.

Prefer:

```text
Read these 3 files, then patch only these 2 files.
```

Avoid:

```text
Analyze the whole project and improve the chatbot.
```

## Code Style Rules

Write compact, reusable Python.

Avoid endless `if/elif/else` chains for routing, classification, validation, and branching.

Prefer:

* dictionaries / dispatch maps
* small pure functions
* dataclasses or Pydantic schemas
* typed return objects
* reusable helpers
* clear module boundaries
* config-driven rules where practical

Bad pattern:

```python
if intent == "pricing":
    ...
elif intent == "contact":
    ...
elif intent == "audit":
    ...
elif intent == "faq":
    ...
```

Better pattern:

```python
handlers = {
    "answer": handle_answer,
    "intake": handle_intake,
    "contact": handle_contact,
    "boundary": handle_boundary,
}

handler = handlers.get(mode, handle_fallback)
return handler(context)
```

## Chatbot Engineering Rules

The bot should not behave like a loose general-purpose assistant.

Core rules:

* One orchestrator.
* Few modes.
* Facts come from retrieved evidence.
* Intake is short.
* The LLM may polish, summarize, classify, or extract.
* The LLM must not invent pricing, case studies, integrations, timelines, guarantees, or business claims.
* If grounding fails, the bot should say it does not have enough information and offer contact or intake.
* If the conversation loops, summarize and hand off instead of asking more questions.

## Testing Strategy

Testing should be efficient, not massive.

Use four layers:

### 1. Unit Tests

Use these for pure logic.

Test:

* mode detection
* grounding thresholds
* lead scoring
* slot extraction
* repeat detection
* handoff decision logic
* forbidden-claim blocking

These should be fast and deterministic.

### 2. Scenario Regression Tests

Use YAML or JSON chatbot scenarios.

Each scenario should include:

```yaml
name:
messages:
expected_mode:
must_include:
must_not_include:
expected_handoff:
```

Start with 30–40 scenarios, not 100+.

Cover:

* pricing questions
* contact requests
* workflow audit requests
* vague business help
* off-topic messages
* repeated user frustration
* missing KB evidence
* attempted prompt injection
* user asks for unsupported guarantee
* user asks for fake case study

### 3. Integration Tests

Use these only where systems touch.

Test:

* session creation
* message endpoint
* KB retrieval
* lead creation
* intake handoff
* email/notification mock
* test mode with zero OpenAI calls

Do not integration-test every tiny branch.

### 4. Smoke Tests

Use these before deployment.

Test:

* widget loads
* user can send a message
* FAQ answer returns
* intake flow completes
* lead is saved
* contact handoff appears
* bot does not call OpenAI when test mode is enabled

## Test Efficiency Rules

Do not build a giant test suite before the feature works.

Use this order:

1. Unit tests for core logic.
2. 10 critical scenario tests.
3. API integration tests.
4. Expand to 30–40 regression scenarios before production.
5. Add only new tests when a real failure is found.

Every test should protect against a real risk.

Avoid tests that only prove implementation details.

## Modular Python Layout

For chatbot work, prefer this structure:

```text
company_chatbot/
  orchestrator.py
  modes.py
  retrieval.py
  grounding.py
  intake.py
  lead_scoring.py
  guards.py
  schemas.py
  prompts.py
  config.py
```

Each file should have a clear job.

`orchestrator.py` should coordinate.

It should not contain all business rules.

## Acceptance Standard

A feature is ready when:

* It solves the target use case.
* It does not touch unrelated systems.
* It has focused tests.
* It has no obvious hardcoded spaghetti.
* It can run in test mode without paid model calls.
* It is easy to remove, replace, or extend.
* It does not regress the client chatbot product.
