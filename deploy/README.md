# Deploying HotSeat to AWS Lambda — step by step

Takes ~15 minutes in the AWS console. Do it once; the MCP endpoint stays up.

## 0. Build the zip (Muse does this)

```bash
cd ~/workspace/hackathon-build-ship-shape/hotseat
bash deploy/package.sh
# -> deploy/hotseat-lambda.zip
```

## 1. Create the DynamoDB table

Console > DynamoDB > Create table:
- Table name: `hotseat-sessions`
- Partition key: `session_id` (String)
- Billing mode: **On-demand** (pay per request — pennies)

## 2. Create the IAM role

Console > IAM > Roles > Create role:
- Trusted entity: **AWS service > Lambda**
- Permissions: create an inline policy, paste `deploy/iam-policy.json`
  (Bedrock invoke on our model, DynamoDB R/W on our table, Polly, logs —
  nothing else)
- Role name: `hotseat-lambda-role`

## 3. Create the Lambda function

Console > Lambda > Create function:
- Name: `hotseat-mcp`, Runtime: **Python 3.12**, Architecture: x86_64
- Execution role: **Use an existing role** > `hotseat-lambda-role`
- Handler: `src.lambda_handler.handler`
- Memory: 512 MB, Timeout: **60 seconds** (MCP calls take a few seconds)

Then: Code > Upload from > `.zip file` > select `deploy/hotseat-lambda.zip`.

## 4. Environment variables

Configuration > Environment variables:
- `HOTSEAT_SESSIONS_TABLE` = `hotseat-sessions`
- `AWS_REGION` = `us-east-2`
- `BEDROCK_MODEL_ID` = `global.anthropic.claude-sonnet-4-6-v1:0`
- `MCP_STATELESS` = `1` (each Lambda invocation independent — required)

(No API keys — Lambda's IAM role provides credentials automatically.)

## 5. Make it public

Configuration > Function URL > Create:
- Auth type: **NONE** (public MCP endpoint — required for the Alexa+ track)

You'll get a URL like `https://abc123.lambda-url.us-east-2.on.aws/`.
**The MCP endpoint is that URL + `/mcp`.**

## 5b. Allow the Function URL host (important!)

The MCP server rejects unknown Host headers (DNS-rebinding protection).
After creating the Function URL, copy just the hostname
(`abc123.lambda-url.us-east-2.on.aws` — no `https://`) and add one more
environment variable:
- `MCP_ALLOWED_HOSTS` = `abc123.lambda-url.us-east-2.on.aws`

Then redeploy the function (Deploy > Deploy) so the new var takes effect.

## 6. Smoke test

```bash
curl -X POST https://<your-url>/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

You should see our 4 tools listed. HotSeat is live. 🔥

## Cost

Lambda free tier: 1M requests/month. DynamoDB on-demand: pennies for our
volume. Bedrock: fractions of a cent per turn. Well inside your credits.
