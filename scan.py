import anthropic
import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# 1. Figure out which files changed in this push
# ---------------------------------------------------------------------------

def get_changed_files():
    # GitHub Actions sets these env vars on every push
    before = os.environ.get("BEFORE_SHA")
    after = os.environ.get("AFTER_SHA")

    if not before or not after or before == "0000000000000000000000000000000000000000":
        # First push to a new branch — just scan everything tracked
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True
        )
        files = result.stdout.strip().splitlines()
    else:
        result = subprocess.run(
            ["git", "diff", "--name-only", before, after],
            capture_output=True, text=True
        )
        files = result.stdout.strip().splitlines()

    # Filter to code files only — skip images, lock files, etc.
    extensions = {".js", ".ts", ".py", ".java", ".php", ".go", ".rb", ".cs", ".cpp", ".c", ".h"}
    return [f for f in files if os.path.splitext(f)[1] in extensions and os.path.isfile(f)]


# ---------------------------------------------------------------------------
# 2. Scan a single file with Claude
# ---------------------------------------------------------------------------

def scan_file(client, filepath):
    with open(filepath, "r", errors="ignore") as f:
        code = f.read()

    if not code.strip():
        return None

    print(f"\n{'='*60}")
    print(f"Scanning: {filepath}")
    print('='*60)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are a security code reviewer. Analyze the following code for security vulnerabilities.

For each vulnerability found, respond in this exact format:
VULN: <vulnerability type>
FILE: {filepath}
SEVERITY: <critical|high|medium|low>
LOCATION: <function name or line description>
DETAIL: <brief explanation and why it matters>
---

If no vulnerabilities are found, respond with: NO_ISSUES_FOUND

Code to review:
