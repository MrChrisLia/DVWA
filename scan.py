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

    if (
        not before
        or not after
        or before == "0000000000000000000000000000000000000000"
    ):
        # First push to a new branch — just scan everything tracked
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True
        )
        files = result.stdout.strip().splitlines()
    else:
        result = subprocess.run(
            ["git", "diff", "--name-only", before, after],
            capture_output=True,
            text=True
        )
        files = result.stdout.strip().splitlines()

    # Filter to code files only — skip images, lock files, etc.
    extensions = {
        ".js", ".ts", ".py", ".java", ".php",
        ".go", ".rb", ".cs", ".cpp", ".c", ".h"
    }

    return [
        f for f in files
        if os.path.splitext(f)[1] in extensions and os.path.isfile(f)
    ]


# ---------------------------------------------------------------------------
# 2. Scan a single file with Claude
# ---------------------------------------------------------------------------

def scan_file(client, filepath):
    with open(filepath, "r", errors="ignore") as f:
        code = f.read()

    if not code.strip():
        return None

    print(f"\n{'=' * 60}")
    print(f"Scanning: {filepath}")
    print("=" * 60)

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

{code}
"""
            }
        ]
    )

    return message.content[0].text


# ---------------------------------------------------------------------------
# 3. Parse findings and decide whether to fail the pipeline
# ---------------------------------------------------------------------------

def parse_severity(findings_text):
    findings_lower = findings_text.lower()

    critical = findings_lower.count("severity: critical")
    high = findings_lower.count("severity: high")
    medium = findings_lower.count("severity: medium")
    low = findings_lower.count("severity: low")

    return critical, high, medium, low


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main():
    # reads ANTHROPIC_API_KEY from env
    client = anthropic.Anthropic()

    changed_files = get_changed_files()

    if not changed_files:
        print("No scannable code files changed in this push. Skipping.")
        sys.exit(0)

    print(f"Files to scan: {changed_files}")

    all_findings = []
    total_critical = 0
    total_high = 0

    for filepath in changed_files:
        findings = scan_file(client, filepath)

        if findings and "NO_ISSUES_FOUND" not in findings:
            print(findings)

            all_findings.append(findings)

            c, h, m, l = parse_severity(findings)

            total_critical += c
            total_high += h
        else:
            print("No issues found.")

    # -----------------------------------------------------------------------
    # 5. Summary
    # -----------------------------------------------------------------------

    print("\n" + "=" * 60)
    print("SCAN SUMMARY")
    print("=" * 60)

    print(f"Files scanned     : {len(changed_files)}")
    print(f"Files with issues : {len(all_findings)}")
    print(f"Critical          : {total_critical}")
    print(f"High              : {total_high}")

    if total_critical > 0:
        print("\n❌ Pipeline failed — critical vulnerabilities found.")
        sys.exit(1)

    elif total_high > 0:
        print("\n⚠️ High severity issues found — review recommended.")
        sys.exit(0)

    else:
        print("\n✅ No critical or high severity issues found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
