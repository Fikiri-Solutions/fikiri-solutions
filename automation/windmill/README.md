# Windmill CE development workspace notes
#
# Sync (after local Windmill is up and you have a workspace token):
#   npm install -g windmill-cli
#   wmill workspace add fikiri-dev http://127.0.0.1:8000 --token <development-token>
#   cd automation/windmill && wmill sync pull   # or push after init
#
# Script: f/normalize_leads/normalize_leads.py
# Requires Fikiri repo on PYTHONPATH or FIKIRI_ROOT when the worker runs the script
# from this checkout. Pure logic is tested via pytest on core.automation_normalize_leads.
#
# Do not configure MCP, production Git promotion, or broad workspace tokens here.
