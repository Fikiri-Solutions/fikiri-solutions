"""Root pytest hooks (repo-wide collection rules)."""

# scripts/test_navigation.py is a manual CLI checker, not part of the unit suite.
collect_ignore = ["scripts"]
