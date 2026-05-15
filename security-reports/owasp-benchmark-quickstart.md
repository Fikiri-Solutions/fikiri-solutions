# OWASP Benchmark Quickstart (Custom Tool Evidence)

Use this when submitting CASA evidence with custom SAST/DAST tools.

## Choose Benchmark Track

- Java Benchmark (mature, widely used in assessor workflows)
- Python Benchmark (newer track; useful for Python-heavy apps)

## Prerequisites (Java track)

- Git
- Maven (3.2.3+)
- Java (7/8 as required by Benchmark docs)

## Run Java Benchmark

```bash
git clone https://github.com/OWASP-Benchmark/BenchmarkJava
cd BenchmarkJava/benchmark
mvn compile
./runBenchmark.sh
```

Benchmark target app is typically available at `https://localhost:8443/benchmark/`.

## Run Python Benchmark (optional/additional)

Use the OWASP Benchmark for Python repository and follow its project README run instructions.
Store outputs under the same evidence folders listed below.

Python Benchmark status snapshot:
- Current preliminary release: v0.1
- Approximate test volume: 1,230 test cases
- Includes categories such as SQLi (CWE-89), XSS (CWE-79), XXE (CWE-611), Command Injection (CWE-78), Redirects (CWE-601), and more.
- Use `expectedresults-VERSION#.csv` from benchmark root during scorecard reconciliation.

## Save tool output with required naming

Include benchmark version + tool name + tool version, e.g.:

`Benchmark_1.2-toolname-v3.0.xml`

Place scan outputs under:

- `security-reports/owasp-benchmark-results/`

## Generate scorecards

From Benchmark repo:

```bash
sh createScorecards.sh
```

Place generated scorecards under:

- `security-reports/owasp-benchmark-scorecards/`

## Recommendation

For CASA custom-tool evidence, include at least one complete scorecard set and map findings back to required CWEs in `casa-cwe-pass-fail.*`.
When using Python Benchmark outputs, record benchmark version in artifact names to avoid expected-results mismatch.
