"""DynamoDB session store — production memory on AWS.

THE LESSON: DynamoDB is AWS's NoSQL database. Think of it as a giant
persistent dict in the cloud:

  - TABLE ......... like one big dict ("hotseat-sessions")
  - PARTITION KEY . the lookup key — ours is "session_id" (a string).
                  Every item MUST have one; it's how DynamoDB finds your row.
  - ITEM .......... one row = one session, stored as a JSON document.
  - PAY-PER-REQUEST billing: no servers, no idle cost. You pay per read/write.
                  A hackathon's worth of sessions costs pennies.

We store each Session as its pydantic JSON under the session_id key.
get() -> fetch item -> validate back into a Session.
save() -> dump Session to JSON -> put item.

Table creation (one-time, in your AWS console or CLI):
  aws dynamodb create-table --table-name hotseat-sessions \\
    --attribute-definitions AttributeName=session_id,AttributeType=S \\
    --key-schema AttributeName=session_id,KeyType=HASH \\
    --billing-mode PAY_PER_REQUEST --region us-east-2
"""

from __future__ import annotations

import os

import boto3

from ..models.session import Session

REGION = os.environ.get("AWS_REGION", "us-east-2")


class DynamoDBSessionStore:
    """Sessions live in DynamoDB. Survives restarts, works across Lambda invocations."""

    def __init__(self, table_name: str, region: str = REGION) -> None:
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def get(self, session_id: str) -> Session | None:
        resp = self.table.get_item(Key={"session_id": session_id})
        item = resp.get("Item")
        if not item:
            return None
        return Session.model_validate_json(item["data"])

    def save(self, session: Session) -> None:
        self.table.put_item(
            Item={"session_id": session.session_id, "data": session.model_dump_json()}
        )
