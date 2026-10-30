#!/usr/bin/env bash
# Claude Code con modelos gratis de OpenRouter, solo en esta terminal (plan de respaldo si se acaba la cuota de Claude).
# Uso: claude-openrouter.sh [argumentos de claude]   |   OR_MODEL=<id> claude-openrouter.sh
# Los modelos gratis pueden registrar lo que reciben: sin código de la empresa (misma regla que openrouter.sh).
set -euo pipefail

KEY="${OPENROUTER_API_KEY:-}"
if [[ -z "$KEY" ]] && command -v powershell >/dev/null; then
  KEY=$(powershell -NoProfile -c "[Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY','User')" | tr -d '\r\n')
fi
[[ -z "$KEY" ]] && { echo "OPENROUTER_API_KEY no está configurada" >&2; exit 3; }

# Tiene que soportar herramientas; los gratis que sí: ver el filtro 'tools' en openrouter.sh --list.
MODEL="${OR_MODEL:-poolside/laguna-s-2.1:free}"
MODEL_CHICO="${OR_MODEL_CHICO:-poolside/laguna-xs-2.1:free}"

export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$KEY"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_FABLE_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_SONNET_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$MODEL_CHICO"
export CLAUDE_CODE_SUBAGENT_MODEL="$MODEL"
# Claude Code no conoce estos modelos y asume 200K; laguna trae 262K.
export CLAUDE_CODE_MAX_CONTEXT_TOKENS="${OR_CONTEXTO:-262144}"

echo "Claude Code vía OpenRouter: $MODEL (chico: $MODEL_CHICO)" >&2
exec claude "$@"
