"""AWS Lambda entry point for the HotSeat MCP server.

THE LESSON: Lambda runs functions, not servers. Our app is a Starlette ASGI
app (it expects to live forever, handling request after request). Mangum is
the adapter: it translates each Lambda event ("a request arrived") into the
ASGI messages our app understands, then translates the response back.

  API Gateway / Function URL  --event-->  handler(event, context)
      --ASGI-->  our Starlette app  --ASGI-->  Mangum  --response-->  caller

Two serverless gotchas we hit, and how we solved them:
  1. SESSIONS: Lambda freezes between invocations, so the in-memory dict would
     lose data. The DynamoDB store fixes this — set HOTSEAT_SESSIONS_TABLE.
  2. LIFESPAN: the MCP SDK's session manager runs its startup lifespan exactly
     once per app instance, but Mangum re-runs lifespan on every invocation
     (including warm ones). So we build a FRESH app per invocation. The
     per-request overhead is tiny (object wiring + starting a task group).

Also note: Strands agents + Bedrock are used here (not mocks) because Lambda
runs with an IAM role — make_client() sees the role's credentials and picks
the real backend automatically. No API keys in code, ever.
"""

from __future__ import annotations

import os

# Region must be set before boto3 clients are created.
os.environ.setdefault("AWS_REGION", "us-east-2")


def handler(event, context):
    """Lambda entry point. Builds a fresh app per invocation (see module docstring)."""
    from mangum import Mangum

    from .server import create_app

    return Mangum(create_app())(event, context)
