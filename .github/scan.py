import anthropic
import os
import sys

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env automatically

# Read a file to scan (start simple, one file at a time)
target_file = "routes/userRouter.js"  # example file in Juice Shop

with open(target_file, "r") as f:
    code = f.read()

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": f"""Review this code for security vulnerabilities.
For each vulnerability found, state:
- Vulnerability type
- Line number or function name
- Severity (critical/high/medium/low)
- Brief explanation

Code:
{code}"""
        }
    ]
)

findings = message.content[0].text
print(findings)

# Fail the pipeline if critical issues found
if "critical" in findings.lower():
    sys.exit(1)  # non-zero exit code = pipeline fails
