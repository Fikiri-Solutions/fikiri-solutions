#!/usr/bin/env python3
"""
CASA Workbench

Runs OAuth-scoped security checks (optional), maps results to prioritized CASA
requirements, and generates lab-ready evidence artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


OAUTH_SCOPE = [
    "routes/auth.py",
    "routes/integrations.py",
    "routes/google_risc.py",
    "routes/user.py",
    "core/app_oauth.py",
    "core/oauth_token_manager.py",
    "core/jwt_auth.py",
    "core/secure_sessions.py",
    "core/security.py",
    "core/google_risc.py",
    "integrations/gmail",
    "integrations/outlook",
    "frontend/src/pages/GmailConnect.tsx",
    "frontend/src/components/GmailConnection.tsx",
    "frontend/src/components/OutlookConnection.tsx",
    "frontend/src/services/apiClient.ts",
]


BLOCKER_REQUIREMENTS = [
    # Access control and server-side enforcement
    {"id": "1.4.1", "chapter": "Architecture", "cwe": "602", "title": "Server-side access control enforcement"},
    {"id": "4.1.1", "chapter": "Access Control", "cwe": "602", "title": "Trusted service layer enforcement"},
    {"id": "4.1.3", "chapter": "Access Control", "cwe": "285", "title": "Least privilege"},
    {"id": "4.2.1", "chapter": "Access Control", "cwe": "639", "title": "IDOR prevention"},
    {"id": "13.1.4", "chapter": "API", "cwe": "285", "title": "URI + resource authorization"},
    # Session and token handling
    {"id": "3.3.1", "chapter": "Session", "cwe": "613", "title": "Session invalidation on logout/expiration"},
    {"id": "3.4.1", "chapter": "Session", "cwe": "614", "title": "Secure cookies"},
    {"id": "3.4.2", "chapter": "Session", "cwe": "1004", "title": "HttpOnly cookies"},
    {"id": "3.4.3", "chapter": "Session", "cwe": "1275", "title": "SameSite cookies"},
    {"id": "3.5.3", "chapter": "Session", "cwe": "345", "title": "Token integrity protections"},
    # Input/injection defenses
    {"id": "5.1.1", "chapter": "Validation", "cwe": "235", "title": "HTTP parameter pollution defense"},
    {"id": "5.1.5", "chapter": "Validation", "cwe": "601", "title": "Safe redirects/forwards"},
    {"id": "5.2.6", "chapter": "Validation", "cwe": "918", "title": "SSRF prevention"},
    {"id": "5.3.3", "chapter": "Validation", "cwe": "79", "title": "XSS prevention"},
    {"id": "5.3.4", "chapter": "Validation", "cwe": "89", "title": "Injection-safe queries"},
    {"id": "5.3.8", "chapter": "Validation", "cwe": "78", "title": "Command injection prevention"},
    # Data leakage and logging
    {"id": "13.1.3", "chapter": "API", "cwe": "598", "title": "No sensitive data in URLs"},
    {"id": "8.2.2", "chapter": "Data Protection", "cwe": "922", "title": "No sensitive browser storage"},
    {"id": "8.3.1", "chapter": "Data Protection", "cwe": "319", "title": "No sensitive query parameters"},
    {"id": "7.1.1", "chapter": "Logging", "cwe": "532", "title": "No credentials in logs"},
    # Build and deploy
    {"id": "14.1.1", "chapter": "Configuration", "cwe": "NA", "title": "Secure repeatable build/deploy"},
    {"id": "14.1.4", "chapter": "Configuration", "cwe": "NA", "title": "Automated redeploy runbook"},
    {"id": "14.3.2", "chapter": "Configuration", "cwe": "497", "title": "Debug disabled in production"},
]


ACCEPTED_FRAMEWORKS = [
    "SOC 2",
    "NIST 800-53 rev4",
    "NIST 800-53 rev5",
    "ISO 27002 v2022",
    "NIST 800-171A",
    "NIST 800-172",
    "ISO 27701 v2019",
    "FedRAMP (all levels)",
    "CIS CSC v8",
    "IEC 62443-4-2",
    "COBIT 2019",
]


REQ_TO_TOOLS = {
    "1.4.1": {"semgrep", "zap"},
    "4.1.1": {"semgrep", "zap"},
    "4.1.3": {"semgrep", "zap"},
    "4.2.1": {"semgrep", "zap"},
    "13.1.4": {"semgrep", "zap"},
    "3.3.1": {"semgrep", "zap"},
    "3.4.1": {"semgrep", "zap"},
    "3.4.2": {"semgrep", "zap"},
    "3.4.3": {"semgrep", "zap"},
    "3.5.3": {"semgrep", "zap"},
    "5.1.1": {"semgrep", "zap"},
    "5.1.5": {"semgrep", "zap"},
    "5.2.6": {"semgrep", "zap"},
    "5.3.3": {"semgrep", "zap"},
    "5.3.4": {"semgrep", "zap"},
    "5.3.8": {"semgrep", "zap"},
    "13.1.3": {"gitleaks", "semgrep", "zap"},
    "8.2.2": {"semgrep", "zap"},
    "8.3.1": {"semgrep", "zap"},
    "7.1.1": {"gitleaks", "semgrep"},
    "14.1.1": {"pip-audit", "npm-audit", "osv"},
    "14.1.4": {"pip-audit", "npm-audit", "osv"},
    "14.3.2": {"semgrep"},
}


@dataclass
class Finding:
    tool: str
    severity: str
    title: str
    cwes: Set[str]
    file_path: str


def run_cmd(command: List[str], cwd: Path, allow_fail: bool = False) -> int:
    print(f"[run] {' '.join(command)}")
    proc = subprocess.run(command, cwd=str(cwd), check=False)
    if proc.returncode != 0 and not allow_fail:
        raise RuntimeError(f"Command failed: {' '.join(command)}")
    return proc.returncode


def ensure_report_dir(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)


def detect_cwes(text: str) -> Set[str]:
    if not text:
        return set()
    return set(re.findall(r"CWE-?(\d+)", text, flags=re.IGNORECASE))


def normalize_severity(value: Optional[str]) -> str:
    if value is None:
        return "unknown"
    val = str(value).strip().lower()
    if val in {"error", "critical"}:
        return "critical"
    if val in {"warning", "high"}:
        return "high"
    if val in {"medium", "moderate", "2"}:
        return "medium"
    if val in {"low", "1"}:
        return "low"
    if val in {"3", "4"}:
        return "high"
    return val or "unknown"


def map_fluid_severity(value: str) -> str:
    val = (value or "").strip().lower()
    if val in {"critical", "high"}:
        return val
    if val in {"medium", "moderate"}:
        return "medium"
    if val in {"low", "informational", "info"}:
        return "low"
    return "unknown"


def parse_semgrep(path: Path) -> List[Finding]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    findings: List[Finding] = []
    for r in data.get("results", []):
        extra = r.get("extra", {})
        metadata = extra.get("metadata", {})
        cwes = set()
        cwe_meta = metadata.get("cwe")
        if isinstance(cwe_meta, list):
            for item in cwe_meta:
                cwes |= detect_cwes(str(item))
        elif cwe_meta:
            cwes |= detect_cwes(str(cwe_meta))
        cwes |= detect_cwes(extra.get("message", ""))
        findings.append(
            Finding(
                tool="semgrep",
                severity=normalize_severity(extra.get("severity")),
                title=extra.get("message", r.get("check_id", "semgrep-finding")),
                cwes=cwes,
                file_path=r.get("path", ""),
            )
        )
    return findings


def parse_gitleaks(path: Path) -> List[Finding]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("findings", [])
    findings: List[Finding] = []
    for item in items:
        findings.append(
            Finding(
                tool="gitleaks",
                severity="high",
                title=item.get("Description", "Potential secret detected"),
                cwes={"798", "532"},
                file_path=item.get("File", ""),
            )
        )
    return findings


def parse_pip_audit(path: Path) -> List[Finding]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    findings: List[Finding] = []
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            aliases = vuln.get("aliases", [])
            findings.append(
                Finding(
                    tool="pip-audit",
                    severity=normalize_severity(vuln.get("severity") or "high"),
                    title=f"{dep.get('name', 'dependency')} {aliases}",
                    cwes=set(),
                    file_path="requirements.txt",
                )
            )
    return findings


def parse_npm_audit(path: Path) -> List[Finding]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    findings: List[Finding] = []
    for name, details in data.get("vulnerabilities", {}).items():
        findings.append(
            Finding(
                tool="npm-audit",
                severity=normalize_severity(details.get("severity")),
                title=f"{name}: {details.get('title', 'npm vulnerability')}",
                cwes=set(),
                file_path=f"frontend/package-lock.json",
            )
        )
    return findings


def parse_osv(path: Path) -> List[Finding]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    findings: List[Finding] = []
    for result in data.get("results", []):
        for pkg in result.get("packages", []):
            for vuln in pkg.get("vulnerabilities", []):
                severity = "medium"
                db_sev = vuln.get("database_specific", {}).get("severity")
                if db_sev:
                    severity = normalize_severity(db_sev)
                findings.append(
                    Finding(
                        tool="osv",
                        severity=severity,
                        title=vuln.get("id", "osv-vulnerability"),
                        cwes=set(),
                        file_path=pkg.get("package", {}).get("name", ""),
                    )
                )
    return findings


def parse_zap(path: Path) -> List[Finding]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    findings: List[Finding] = []
    for site in data.get("site", []):
        for alert in site.get("alerts", []):
            cwe = str(alert.get("cweid", "")).strip()
            cwes = {cwe} if cwe and cwe != "0" else set()
            findings.append(
                Finding(
                    tool="zap",
                    severity=normalize_severity(alert.get("riskdesc", alert.get("riskcode", ""))),
                    title=alert.get("name", "zap-alert"),
                    cwes=cwes,
                    file_path=site.get("@name", ""),
                )
            )
    return findings


def parse_fluid_csv(path: Path) -> List[Finding]:
    if not path.exists():
        return []
    findings: List[Finding] = []
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            title = row.get("title") or row.get("vulnerability") or row.get("finding") or "fluid-finding"
            severity = map_fluid_severity(row.get("severity", ""))
            cwes = detect_cwes(" ".join([row.get("cwe", ""), row.get("description", ""), title]))
            file_path = row.get("where") or row.get("location") or row.get("path") or ""
            findings.append(
                Finding(
                    tool="fluidattacks",
                    severity=severity,
                    title=title,
                    cwes=cwes,
                    file_path=file_path,
                )
            )
    return findings


def has_blocker(findings: List[Finding]) -> bool:
    return any(f.severity in {"critical", "high"} for f in findings)


def findings_for_requirement(requirement: Dict[str, str], findings: List[Finding]) -> List[Finding]:
    req_id = requirement["id"]
    cwe = requirement.get("cwe", "NA")
    tools = REQ_TO_TOOLS.get(req_id, set())
    matched: List[Finding] = []
    for finding in findings:
        if finding.tool not in tools:
            continue
        if cwe != "NA" and cwe in finding.cwes:
            matched.append(finding)
            continue
        if cwe == "NA":
            matched.append(finding)
            continue
        # If CWE is not tagged by tool, still map by tool for manual triage.
        if finding.tool in {"gitleaks", "pip-audit", "npm-audit", "osv"}:
            matched.append(finding)
    return matched


def summarize_tool_counts(findings: List[Finding]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for f in findings:
        tool_bucket = summary.setdefault(f.tool, {"critical": 0, "high": 0, "medium": 0, "low": 0, "other": 0})
        sev = f.severity if f.severity in tool_bucket else "other"
        tool_bucket[sev] += 1
    return summary


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    fields = [
        "requirement_id",
        "chapter",
        "cwe",
        "title",
        "status",
        "blocking_findings",
        "tools_used",
        "evidence_files",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: List[Dict[str, str]], tool_summary: Dict[str, Dict[str, int]], gate_passed: bool) -> None:
    lines = []
    lines.append("# CASA Pre-Lab Evidence Report")
    lines.append("")
    lines.append(f"Gate decision: **{'PASS' if gate_passed else 'FAIL'}**")
    lines.append("")
    lines.append("## Tool Summary")
    lines.append("")
    for tool, counts in sorted(tool_summary.items()):
        lines.append(
            f"- `{tool}` -> critical: {counts['critical']}, high: {counts['high']}, medium: {counts['medium']}, low: {counts['low']}"
        )
    lines.append("")
    lines.append("## Requirement Mapping")
    lines.append("")
    lines.append("| Requirement | CWE | Status | Blocking Findings | Tools |")
    lines.append("|---|---:|---|---:|---|")
    for row in rows:
        lines.append(
            f"| {row['requirement_id']} | {row['cwe']} | {row['status']} | {row['blocking_findings']} | {row['tools_used']} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `FAIL` means at least one high/critical finding is mapped to the requirement.")
    lines.append("- `REVIEW` means no blocker found, but manual confirmation/evidence is still expected.")
    lines.append("- Attach scanner JSON files with this report to reduce lab back-and-forth.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ast_txt_summaries(report_dir: Path) -> None:
    mappings = [
        ("semgrep.json", "ast-semgrep-results.txt"),
        ("gitleaks.json", "ast-gitleaks-results.txt"),
        ("pip-audit.json", "ast-pip-audit-results.txt"),
        ("npm-audit.json", "ast-npm-audit-results.txt"),
        ("osv-scanner.json", "ast-osv-scanner-results.txt"),
        ("zap-report.json", "ast-zap-results.txt"),
        ("fluidattacks-results.csv", "ast-fluidattacks-results.txt"),
    ]
    for src_name, out_name in mappings:
        src = report_dir / src_name
        out = report_dir / out_name
        if src.exists():
            content = src.read_text(encoding="utf-8", errors="replace")
            out.write_text(content, encoding="utf-8")


def write_cwe_pass_fail_outputs(report_dir: Path, required_cwes: List[str], failed_cwes: List[str]) -> None:
    failed_set = set(failed_cwes)
    csv_path = report_dir / "casa-cwe-pass-fail.csv"
    xml_path = report_dir / "casa-cwe-pass-fail.xml"

    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["cwe", "status"])
        writer.writeheader()
        for cwe in required_cwes:
            writer.writerow({"cwe": cwe, "status": "FAIL" if cwe in failed_set else "PASS"})

    root = ET.Element("casa_cwe_results")
    summary = ET.SubElement(root, "summary")
    ET.SubElement(summary, "total_cwes").text = str(len(required_cwes))
    ET.SubElement(summary, "failed_cwes").text = str(len(failed_cwes))
    ET.SubElement(summary, "passed_cwes").text = str(len(required_cwes) - len(failed_cwes))

    results = ET.SubElement(root, "results")
    for cwe in required_cwes:
        result = ET.SubElement(results, "cwe_result")
        ET.SubElement(result, "cwe").text = cwe
        ET.SubElement(result, "status").text = "FAIL" if cwe in failed_set else "PASS"

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def write_framework_manifest(report_dir: Path) -> None:
    manifest_path = report_dir / "casa-framework-evidence-template.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "framework",
                "status",
                "evidence_type",
                "artifact_path_or_url",
                "issued_by",
                "issue_date",
                "expiration_date",
                "coverage_notes",
            ],
        )
        writer.writeheader()
        for framework in ACCEPTED_FRAMEWORKS:
            writer.writerow(
                {
                    "framework": framework,
                    "status": "missing",
                    "evidence_type": "",
                    "artifact_path_or_url": "",
                    "issued_by": "",
                    "issue_date": "",
                    "expiration_date": "",
                    "coverage_notes": "",
                }
            )

    guidance_path = report_dir / "casa-framework-evidence-guide.md"
    guidance_lines = [
        "# CASA Accepted Framework Evidence Guide",
        "",
        "Use this guide to reduce redundant testing by attaching accepted framework artifacts.",
        "",
        "## Expected evidence examples",
        "",
        "- `SOC 2`: independent audit report or assessor attestation letter",
        "- `NIST 800-53 rev4/rev5`: independent audit report or assessor attestation letter",
        "- `ISO 27002 v2022`: independent assessment report",
        "- `NIST 800-171A` / `NIST 800-172`: independent audit report or assessor attestation letter",
        "- `ISO 27701 v2019`: independent audit report or assessor attestation letter",
        "- `FedRAMP`: 3PAO attestation letter or FedRAMP marketplace listing screenshot",
        "- `CIS CSC v8`: compliance dashboard screenshot, self-assessment, or independent audit report",
        "- `IEC 62443-4-2`: ISASecure certification artifact",
        "- `COBIT 2019`: COBIT self-assessment report based on CMMI",
        "",
        "## How to use",
        "",
        "1. Fill `casa-framework-evidence-template.csv` with available artifacts.",
        "2. Add file paths/URLs for each artifact and dates to avoid expired evidence.",
        "3. Include this file in your assessor evidence package with scanner reports.",
    ]
    guidance_path.write_text("\n".join(guidance_lines) + "\n", encoding="utf-8")


def write_custom_scan_policy(report_dir: Path, required_cwes: List[str]) -> None:
    policy = {
        "policy_name": "casa-tier2-custom-scan-policy",
        "generated_at_utc": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "scope": {
            "type": "oauth-in-scope-components",
            "paths": OAUTH_SCOPE,
        },
        "notes": [
            "CASA self-scan verification is deprecated; this policy supports readiness evidence for lab verification.",
            "For JavaScript/TypeScript codebases, use custom SAST tools that support JS/TS (e.g., Semgrep).",
        ],
        "tools": {
            "dast": [
                {
                    "name": "OWASP ZAP",
                    "mode": "custom-policy",
                    "artifact": "zap-report.json",
                }
            ],
            "sast": [
                {
                    "name": "Semgrep",
                    "mode": "custom-policy",
                    "artifact": "semgrep.json",
                    "language_support": ["python", "javascript", "typescript"],
                },
                {
                    "name": "FluidAttacks CLI",
                    "mode": "optional-preconfigured",
                    "artifact": "fluidattacks-results.csv",
                    "language_support": ["web", "mobile", "api", "serverless", "extension"],
                }
            ],
            "secrets": [{"name": "gitleaks", "artifact": "gitleaks.json"}],
            "dependencies": [
                {"name": "pip-audit", "artifact": "pip-audit.json"},
                {"name": "npm audit", "artifact": "npm-audit.json"},
                {"name": "osv-scanner", "artifact": "osv-scanner.json"},
            ],
        },
        "required_cwes": required_cwes,
    }
    (report_dir / "casa-custom-scan-policy.json").write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")


def write_assessor_upload_checklist(report_dir: Path) -> None:
    checklist = report_dir / "casa-assessor-upload-checklist.md"
    lines = [
        "# CASA Assessor Upload Checklist",
        "",
        "Use this checklist before uploading evidence to the portal.",
        "",
        "## Required core files",
        "",
        "- [ ] `casa-cwe-pass-fail.csv`",
        "- [ ] `casa-cwe-pass-fail.xml`",
        "- [ ] `casa-custom-scan-policy.json` (if using custom tools)",
        "- [ ] AST plain text summaries (`ast-*-results.txt`) for portal compatibility",
        "- [ ] DAST result artifact(s): `zap-report.json` (+ CSV/XML export if available)",
        "- [ ] If full web/mobile DAST was run: `zap-results-full.xml`",
        "- [ ] If API DAST was run: `zap-results-api.xml`",
        "- [ ] SAST result artifact(s): `semgrep.json` (+ CSV/XML export if available)",
        "- [ ] Optional preconfigured SAST result: `fluidattacks-results.csv`",
        "- [ ] If using custom tools: OWASP Benchmark scan output in `owasp-benchmark-results/`",
        "- [ ] If using custom tools: OWASP Benchmark scorecard in `owasp-benchmark-scorecards/`",
        "",
        "## Supporting evidence (recommended)",
        "",
        "- [ ] `casa-evidence-report.md`",
        "- [ ] `casa-evidence-matrix.csv`",
        "- [ ] `casa-required-cwes.txt`",
        "- [ ] `casa-required-cwes.csv`",
        "- [ ] `casa-failed-mapped-cwes.json`",
        "- [ ] `casa-framework-evidence-template.csv`",
        "- [ ] `casa-framework-evidence-guide.md`",
        "",
        "## Optional (if requested by assessor)",
        "",
        "- [ ] OWASP Benchmark scorecard output from selected DAST/SAST tool",
        "",
        "## Gate",
        "",
        "- [ ] No failed mapped CWEs before submission",
    ]
    checklist.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_required_cwe_files(report_dir: Path, requirements: List[Dict[str, str]]) -> List[str]:
    cwes = sorted({r["cwe"] for r in requirements if r.get("cwe") and r["cwe"] != "NA"})
    txt_path = report_dir / "casa-required-cwes.txt"
    csv_path = report_dir / "casa-required-cwes.csv"
    txt_path.write_text("\n".join(cwes) + ("\n" if cwes else ""), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["cwe", "requirement_ids"])
        writer.writeheader()
        for cwe in cwes:
            req_ids = [r["id"] for r in requirements if r.get("cwe") == cwe]
            writer.writerow({"cwe": cwe, "requirement_ids": ",".join(req_ids)})
    return cwes


def write_fluid_scan_quickstart(report_dir: Path) -> None:
    guide = report_dir / "fluidattacks-quickstart.md"
    lines = [
        "# FluidAttacks SAST Quickstart (Readiness)",
        "",
        "Use this only if you want to add FluidAttacks artifacts to your readiness evidence package.",
        "",
        "## Minimal workflow",
        "",
        "1. Create a scan workspace folder.",
        "2. Place CASA scan Dockerfile in that folder.",
        "3. Clone app repo into workspace and place `config.yaml` at repo root.",
        "4. Build container:",
        "   `docker build -t casascan /path/to/Dockerfile`",
        "5. Run scan:",
        "   `docker run casascan m gitlab:fluidattacks/universe@trunk /skims scan {AppRepo}/config.yaml`",
        "6. Copy result CSV from container to host as `fluidattacks-results.csv`.",
        "7. Place `fluidattacks-results.csv` into `security-reports/`.",
        "8. Re-run workbench with `--skip-scans` to include it in mapping outputs.",
        "",
        "## Notes",
        "",
        "- Keep scan output in CSV format for portal compatibility.",
        "- For JavaScript/TypeScript projects, Semgrep remains the primary custom SAST option.",
    ]
    guide.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_benchmark_quickstart(report_dir: Path) -> None:
    guide = report_dir / "owasp-benchmark-quickstart.md"
    lines = [
        "# OWASP Benchmark Quickstart (Custom Tool Evidence)",
        "",
        "Use this when submitting CASA evidence with custom SAST/DAST tools.",
        "",
        "## Choose Benchmark Track",
        "",
        "- Java Benchmark (mature, widely used in assessor workflows)",
        "- Python Benchmark (newer track; useful for Python-heavy apps)",
        "",
        "## Prerequisites (Java track)",
        "",
        "- Git",
        "- Maven (3.2.3+)",
        "- Java (7/8 as required by Benchmark docs)",
        "",
        "## Run Java Benchmark",
        "",
        "```bash",
        "git clone https://github.com/OWASP-Benchmark/BenchmarkJava",
        "cd BenchmarkJava/benchmark",
        "mvn compile",
        "./runBenchmark.sh",
        "```",
        "",
        "Benchmark target app is typically available at `https://localhost:8443/benchmark/`.",
        "",
        "## Run Python Benchmark (optional/additional)",
        "",
        "Use the OWASP Benchmark for Python repository and follow its project README run instructions.",
        "Store outputs under the same evidence folders listed below.",
        "",
        "Python Benchmark status snapshot:",
        "- Current preliminary release: v0.1",
        "- Approximate test volume: 1,230 test cases",
        "- Includes categories such as SQLi (CWE-89), XSS (CWE-79), XXE (CWE-611), Command Injection (CWE-78), Redirects (CWE-601), and more.",
        "- Use `expectedresults-VERSION#.csv` from benchmark root during scorecard reconciliation.",
        "",
        "## Save tool output with required naming",
        "",
        "Include benchmark version + tool name + tool version, e.g.:",
        "",
        "`Benchmark_1.2-toolname-v3.0.xml`",
        "",
        "Place scan outputs under:",
        "",
        "- `security-reports/owasp-benchmark-results/`",
        "",
        "## Generate scorecards",
        "",
        "From Benchmark repo:",
        "",
        "```bash",
        "sh createScorecards.sh",
        "```",
        "",
        "Place generated scorecards under:",
        "",
        "- `security-reports/owasp-benchmark-scorecards/`",
        "",
        "## Recommendation",
        "",
        "For CASA custom-tool evidence, include at least one complete scorecard set and map findings back to required CWEs in `casa-cwe-pass-fail.*`.",
        "When using Python Benchmark outputs, record benchmark version in artifact names to avoid expected-results mismatch.",
    ]
    guide.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_benchmark_evidence(report_dir: Path, custom_tools_mode: bool) -> Tuple[bool, str]:
    results_dir = report_dir / "owasp-benchmark-results"
    scorecards_dir = report_dir / "owasp-benchmark-scorecards"
    has_results = results_dir.exists() and any(results_dir.iterdir())
    has_scorecards = scorecards_dir.exists() and any(scorecards_dir.iterdir())

    status = {
        "custom_tools_mode": custom_tools_mode,
        "results_dir": str(results_dir),
        "scorecards_dir": str(scorecards_dir),
        "has_results": has_results,
        "has_scorecards": has_scorecards,
        "pass": (has_results and has_scorecards) if custom_tools_mode else True,
        "notes": "Benchmark artifacts required only when custom tools mode is enabled.",
    }
    out = report_dir / "owasp-benchmark-evidence-status.json"
    out.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    if not custom_tools_mode:
        return True, "custom-tools mode disabled"
    if has_results and has_scorecards:
        return True, "benchmark evidence present"
    return False, "missing benchmark results or scorecards for custom tools mode"


def write_portal_submission_template(report_dir: Path) -> None:
    template = report_dir / "casa-portal-submission-template.md"
    lines = [
        "# CASA Portal Submission Template",
        "",
        "Fill this before submitting in Tier 2 portal.",
        "",
        "## Case Metadata",
        "",
        "- Project Contact Name:",
        "- Project Contact Email:",
        "- Project Contact Phone:",
        "- Legal Entity Name:",
        "- Website:",
        "- Assessment Type (New/Reassessment):",
        "- Application Scope:",
        "- Google Project ID:",
        "- CASA Notification Email Date:",
        "- CASA Initiation Date:",
        "",
        "## 30-Day Deadline",
        "",
        "- Target submit-by date: (initiation date + 30 days)",
        "- Extension requested? (Y/N):",
        "",
        "## Upload Inventory",
        "",
        "- Security framework artifacts (optional acceleration):",
        "- AST configuration/policy files:",
        "- AST result files (txt/csv/xml/pdf as requested):",
        "- OWASP Benchmark artifacts (required for custom tools):",
        "- Evidence bundle file name:",
        "",
        "## Self-Attestation Notes",
        "",
        "- Requirements needing attestation:",
        "- Response notes for Yes/No/N/A items:",
        "- Requirements auto-fulfilled by portal prerequisites:",
    ]
    template.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_deadline_tracker(report_dir: Path, initiated_date: Optional[str]) -> None:
    tracker = report_dir / "casa-deadline-tracker.json"
    payload: Dict[str, str] = {
        "initiated_date": initiated_date or "",
        "submit_by_date": "",
        "status": "unknown",
        "note": "Set initiated_date via --initiated-date YYYY-MM-DD to compute 30-day deadline.",
    }
    if initiated_date:
        try:
            start = dt.date.fromisoformat(initiated_date)
            deadline = start + dt.timedelta(days=30)
            today = dt.date.today()
            if today <= deadline:
                status = "in_window"
            else:
                status = "overdue"
            payload = {
                "initiated_date": initiated_date,
                "submit_by_date": deadline.isoformat(),
                "status": status,
                "note": "Portal submissions are expected within 30 days of initiation.",
            }
        except ValueError:
            payload["status"] = "invalid_date"
            payload["note"] = "Invalid initiated_date format; expected YYYY-MM-DD."
    tracker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def create_submission_bundle(report_dir: Path) -> Path:
    bundle_path = report_dir / "casa-submission-bundle.zip"
    include_names = [
        "casa-evidence-report.md",
        "casa-evidence-matrix.csv",
        "casa-required-cwes.txt",
        "casa-required-cwes.csv",
        "casa-failed-mapped-cwes.json",
        "casa-framework-evidence-template.csv",
        "casa-framework-evidence-guide.md",
        "casa-custom-scan-policy.json",
        "casa-cwe-pass-fail.csv",
        "casa-cwe-pass-fail.xml",
        "casa-assessor-upload-checklist.md",
        "casa-portal-submission-template.md",
        "casa-deadline-tracker.json",
        "fluidattacks-quickstart.md",
        "owasp-benchmark-quickstart.md",
        "owasp-benchmark-evidence-status.json",
        "zap-results-full.xml",
        "zap-results-api.xml",
        "semgrep.json",
        "gitleaks.json",
        "pip-audit.json",
        "npm-audit.json",
        "osv-scanner.json",
        "zap-report.json",
        "fluidattacks-results.csv",
        "ast-semgrep-results.txt",
        "ast-gitleaks-results.txt",
        "ast-pip-audit-results.txt",
        "ast-npm-audit-results.txt",
        "ast-osv-scanner-results.txt",
        "ast-zap-results.txt",
        "ast-fluidattacks-results.txt",
    ]
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in include_names:
            file_path = report_dir / name
            if file_path.exists() and file_path.is_file():
                zf.write(file_path, arcname=name)
    return bundle_path


def compute_failed_mapped_cwes(findings: List[Finding], required_cwes: List[str]) -> List[str]:
    required = set(required_cwes)
    failed: Set[str] = set()
    for finding in findings:
        if finding.severity not in {"critical", "high"}:
            continue
        for cwe in finding.cwes:
            if cwe in required:
                failed.add(cwe)
    return sorted(failed)


def run_scans(root: Path, report_dir: Path, run_zap: bool, zap_target: str) -> None:
    def tool_exists(name: str) -> bool:
        return shutil.which(name) is not None

    if tool_exists("gitleaks"):
        run_cmd(
            [
                "gitleaks",
                "detect",
                "--source",
                ".",
                "--no-git",
                "--report-format",
                "json",
                "--report-path",
                str(report_dir / "gitleaks.json"),
            ],
            root,
        )
    else:
        print("[skip] gitleaks not installed")

    if tool_exists("semgrep"):
        run_cmd(
            [
                "semgrep",
                "scan",
                "--config",
                "p/owasp-top-ten",
                "--config",
                "p/secrets",
                "--json",
                "--output",
                str(report_dir / "semgrep.json"),
                *OAUTH_SCOPE,
            ],
            root,
        )
    else:
        print("[skip] semgrep not installed")

    if tool_exists("pip-audit"):
        run_cmd(["pip-audit", "-r", "requirements.txt", "-f", "json", "-o", str(report_dir / "pip-audit.json")], root)
    else:
        print("[skip] pip-audit not installed")

    if tool_exists("npm"):
        run_cmd(["npm", "--prefix", "frontend", "audit", "--json"], root, allow_fail=True)
        npm_proc = subprocess.run(
            ["npm", "--prefix", "frontend", "audit", "--json"],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
        )
        (report_dir / "npm-audit.json").write_text(npm_proc.stdout or "{}", encoding="utf-8")
    else:
        print("[skip] npm not installed")

    if tool_exists("osv-scanner"):
        run_cmd(["osv-scanner", "--format", "json", "--output", str(report_dir / "osv-scanner.json"), "."], root)
    else:
        print("[skip] osv-scanner not installed")

    zap_mode = os.getenv("ZAP_MODE", "baseline").strip().lower()
    zap_config = os.getenv("ZAP_CONFIG", "").strip()
    zap_context_file = os.getenv("ZAP_CONTEXT_FILE", "").strip()
    zap_user = os.getenv("ZAP_USER", "").strip()
    zap_api_format = os.getenv("ZAP_API_FORMAT", "openapi").strip()
    zap_port = os.getenv("ZAP_PORT", "8080").strip()

    if run_zap:
        if tool_exists("docker"):
            if zap_mode == "full":
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-t",
                    "-p",
                    f"{zap_port}:{zap_port}",
                    "-v",
                    f"{root / report_dir}:/zap/wrk:rw",
                    "ghcr.io/zaproxy/zaproxy:stable",
                    "zap-full-scan.py",
                    "-t",
                    zap_target,
                    "-P",
                    zap_port,
                    "-x",
                    "zap-results-full.xml",
                    "-J",
                    "zap-report.json",
                ]
                if zap_config:
                    cmd.extend(["-c", zap_config])
                if zap_context_file:
                    cmd.extend(["-n", zap_context_file])
                if zap_user:
                    cmd.extend(["-U", zap_user])
                run_cmd(cmd, root)
            elif zap_mode == "api":
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-t",
                    "-p",
                    f"{zap_port}:{zap_port}",
                    "-v",
                    f"{root / report_dir}:/zap/wrk:rw",
                    "ghcr.io/zaproxy/zaproxy:stable",
                    "zap-api-scan.py",
                    "-t",
                    zap_target,
                    "-f",
                    zap_api_format,
                    "-P",
                    zap_port,
                    "-x",
                    "zap-results-api.xml",
                    "-J",
                    "zap-report.json",
                ]
                if zap_config:
                    cmd.extend(["-c", zap_config])
                run_cmd(cmd, root)
            else:
                run_cmd(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "-t",
                        "-v",
                        f"{root / report_dir}:/zap/wrk:rw",
                        "ghcr.io/zaproxy/zaproxy:stable",
                        "zap-baseline.py",
                        "-t",
                        zap_target,
                        "-r",
                        "zap-report.html",
                        "-J",
                        "zap-report.json",
                    ],
                    root,
                )
        else:
            print("[skip] docker not installed, zap scan skipped")


def main() -> int:
    parser = argparse.ArgumentParser(description="CASA security workbench for OAuth-scope evidence generation")
    parser.add_argument("--report-dir", default="security-reports", help="Directory for scanner outputs and generated evidence")
    parser.add_argument("--skip-scans", action="store_true", help="Skip scanner execution and use existing JSON artifacts")
    parser.add_argument("--run-zap", action="store_true", help="Run OWASP ZAP baseline (requires Docker)")
    parser.add_argument("--zap-target", default="http://host.docker.internal:5000", help="Target URL for ZAP baseline")
    parser.add_argument(
        "--custom-tools-mode",
        action="store_true",
        help="Enable strict custom-tool evidence checks (requires OWASP Benchmark results + scorecards).",
    )
    parser.add_argument("--bundle", action="store_true", help="Create a portal-ready ZIP bundle in security-reports.")
    parser.add_argument("--initiated-date", default="", help="CASA initiation date (YYYY-MM-DD) for deadline tracking.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    report_dir = root / args.report_dir
    ensure_report_dir(report_dir)

    if not args.skip_scans:
        run_scans(root=root, report_dir=Path(args.report_dir), run_zap=args.run_zap, zap_target=args.zap_target)

    all_findings: List[Finding] = []
    all_findings.extend(parse_gitleaks(report_dir / "gitleaks.json"))
    all_findings.extend(parse_semgrep(report_dir / "semgrep.json"))
    all_findings.extend(parse_pip_audit(report_dir / "pip-audit.json"))
    all_findings.extend(parse_npm_audit(report_dir / "npm-audit.json"))
    all_findings.extend(parse_osv(report_dir / "osv-scanner.json"))
    all_findings.extend(parse_zap(report_dir / "zap-report.json"))
    all_findings.extend(parse_fluid_csv(report_dir / "fluidattacks-results.csv"))

    required_cwes = write_required_cwe_files(report_dir, BLOCKER_REQUIREMENTS)
    write_framework_manifest(report_dir)
    write_custom_scan_policy(report_dir, required_cwes)
    write_fluid_scan_quickstart(report_dir)
    write_benchmark_quickstart(report_dir)
    write_portal_submission_template(report_dir)
    write_deadline_tracker(report_dir, args.initiated_date.strip() or None)
    benchmark_ok, benchmark_note = evaluate_benchmark_evidence(report_dir, args.custom_tools_mode)
    failed_mapped_cwes = compute_failed_mapped_cwes(all_findings, required_cwes)
    write_cwe_pass_fail_outputs(report_dir, required_cwes, failed_mapped_cwes)
    write_assessor_upload_checklist(report_dir)
    write_ast_txt_summaries(report_dir)

    rows: List[Dict[str, str]] = []
    gate_passed = len(failed_mapped_cwes) == 0 and benchmark_ok
    evidence_files = [
        "gitleaks.json",
        "semgrep.json",
        "pip-audit.json",
        "npm-audit.json",
        "osv-scanner.json",
        "zap-report.json",
    ]

    for req in BLOCKER_REQUIREMENTS:
        matched = findings_for_requirement(req, all_findings)
        blockers = [f for f in matched if f.severity in {"critical", "high"}]
        if blockers:
            status = "FAIL"
        elif matched:
            status = "REVIEW"
        else:
            status = "PASS"

        rows.append(
            {
                "requirement_id": req["id"],
                "chapter": req["chapter"],
                "cwe": req["cwe"],
                "title": req["title"],
                "status": status,
                "blocking_findings": str(len(blockers)),
                "tools_used": ", ".join(sorted(REQ_TO_TOOLS.get(req["id"], set()))),
                "evidence_files": ", ".join(evidence_files),
                "notes": "Auto-generated. Add endpoint-level triage before lab submission.",
            }
        )

    tool_summary = summarize_tool_counts(all_findings)
    write_csv(report_dir / "casa-evidence-matrix.csv", rows)
    write_markdown(report_dir / "casa-evidence-report.md", rows, tool_summary, gate_passed)

    (report_dir / "casa-failed-mapped-cwes.json").write_text(
        json.dumps({"failed_mapped_cwes": failed_mapped_cwes}, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nGenerated artifacts:")
    print(f"- {report_dir / 'casa-evidence-matrix.csv'}")
    print(f"- {report_dir / 'casa-evidence-report.md'}")
    print(f"- {report_dir / 'casa-required-cwes.txt'}")
    print(f"- {report_dir / 'casa-required-cwes.csv'}")
    print(f"- {report_dir / 'casa-failed-mapped-cwes.json'}")
    print(f"- {report_dir / 'casa-framework-evidence-template.csv'}")
    print(f"- {report_dir / 'casa-framework-evidence-guide.md'}")
    print(f"- {report_dir / 'casa-custom-scan-policy.json'}")
    print(f"- {report_dir / 'casa-cwe-pass-fail.csv'}")
    print(f"- {report_dir / 'casa-cwe-pass-fail.xml'}")
    print(f"- {report_dir / 'casa-assessor-upload-checklist.md'}")
    print(f"- {report_dir / 'fluidattacks-quickstart.md'}")
    print(f"- {report_dir / 'owasp-benchmark-quickstart.md'}")
    print(f"- {report_dir / 'owasp-benchmark-evidence-status.json'}")
    print(f"- {report_dir / 'casa-portal-submission-template.md'}")
    print(f"- {report_dir / 'casa-deadline-tracker.json'}")
    print(f"- {report_dir}/*.json scanner outputs")
    if failed_mapped_cwes:
        print(f"\nFailed mapped CWEs: {', '.join(failed_mapped_cwes)}")
    else:
        print("\nFailed mapped CWEs: none")
    print(f"Benchmark evidence check: {'PASS' if benchmark_ok else 'FAIL'} ({benchmark_note})")
    if args.bundle:
        bundle = create_submission_bundle(report_dir)
        print(f"Submission bundle: {bundle}")
    print(f"CASA pre-lab gate: {'PASS' if gate_passed else 'FAIL'}")
    return 0 if gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
