#!/usr/bin/env bash

set -euo pipefail

# Read-only check of the local prerequisites: the supported-machine contract
# that ./scripts/verify.sh needs, and the tools of the agentic development
# workflow. Uses only Bash builtins besides the tools it checks.

script_dir="${BASH_SOURCE[0]%/*}"
[[ "$script_dir" != "${BASH_SOURCE[0]}" ]] || script_dir="."
root="$script_dir/.."
source "$script_dir/lib/agent.sh"
source "$script_dir/lib/prerequisites.sh"

warn() {
  echo "WARNING  $1"
  echo "         $2"
}

echo "== Doctor =="

# The supported-machine contract: what ./scripts/verify.sh needs.
check_git
check_jq
check_uv
check_elan
if [[ -x "$root/.venv/bin/python" ]]; then
  check_browser "$root/.venv/bin/python"
else
  missing "the locked Python environment is not installed" \
    "Run: uv sync --locked && uv run --locked playwright install --only-shell chromium"
fi

# The agentic development workflow: not needed by verification.
if have gh; then
  ok "GitHub CLI (gh) is installed"
  if gh auth status >/dev/null 2>&1; then
    ok "GitHub CLI is authenticated"
  else
    missing "GitHub CLI is not authenticated" "Run: gh auth login"
  fi
else
  missing "GitHub CLI (gh) is not installed" "Install it: https://cli.github.com"
fi

# Providers that .agents/agents.conf assigns to a role are required.
codex_roles=""
claude_roles=""
if config_error="$( (agent_lookup "$root" implementer) 2>&1)"; then
  if [[ -f "${AGENT_CONFIG_FILE:-$root/.agents/agents.conf}" ]]; then
    ok "agent configuration is valid"
    for role in $AGENT_ROLES; do
      agent_lookup "$root" "$role"
      case "$AGENT_CONFIG_PROVIDER" in
        codex) codex_roles+=" $role" ;;
        claude) claude_roles+=" $role" ;;
        "") ;;
        *)
          missing "role '$role' uses unsupported agent '$AGENT_CONFIG_PROVIDER'" \
            "Use 'codex' or 'claude' in .agents/agents.conf."
          ;;
      esac
    done
  else
    warn "agent configuration .agents/agents.conf was not found" \
      "Every workflow script then needs --agent and --model."
  fi
else
  missing "agent configuration is invalid" "${config_error#Error: }"
fi

for agent in codex claude; do
  roles="${agent}_roles"
  if have "$agent"; then
    ok "$agent CLI is installed"
  elif [[ -n "${!roles}" ]]; then
    missing "$agent CLI is not installed" "It is configured for:${!roles}. Install it or change .agents/agents.conf."
  else
    warn "$agent CLI is not installed" "Install it before selecting '$agent' in a workflow script."
  fi
done

if have git; then
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    ok "current directory is inside a Git repository"
    if git remote get-url origin >/dev/null 2>&1; then
      ok "remote 'origin' is configured"
      # Never prompt and never wait indefinitely on an unresponsive remote.
      if GIT_TERMINAL_PROMPT=0 \
        GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=10" \
        GIT_HTTP_LOW_SPEED_LIMIT=1 GIT_HTTP_LOW_SPEED_TIME=10 \
        git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
        ok "branch 'main' is reachable on origin"
        # Reading a public repository works with any identity; pushing does
        # not. A dry run asks the remote for permission without changing it.
        if GIT_TERMINAL_PROMPT=0 \
          GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=10" \
          GIT_HTTP_LOW_SPEED_LIMIT=1 GIT_HTTP_LOW_SPEED_TIME=10 \
          git push --dry-run --quiet origin HEAD:refs/heads/doctor-push-check >/dev/null 2>&1; then
          ok "you can push to origin"
        else
          missing "you cannot push to origin" \
            "Check that the remote URL uses the GitHub account that owns the repository: git remote get-url origin; ssh -T git@github.com"
        fi
      else
        missing "branch 'main' is not reachable on origin" \
          "Check network access and that origin has a 'main' branch: git ls-remote --heads origin main"
      fi
    else
      missing "remote 'origin' is not configured" "Run: git remote add origin <repository-url>"
    fi
  else
    missing "current directory is not inside a Git repository" "Run this script from the project checkout."
  fi
fi

echo
if [[ "$failed" -ne 0 ]]; then
  echo "Doctor found problems. Fix the FAILED items above and run it again." >&2
  exit 1
fi

echo "All required prerequisites are available."
