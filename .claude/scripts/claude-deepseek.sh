#!/usr/bin/env bash
# Claude Code con DeepSeek (endpoint compatible con Anthropic): coder externo de /orquestar que no gasta cuota de Claude.
# Uso: claude-deepseek.sh [argumentos de claude]   |   DS_MODEL=<id> claude-deepseek.sh -p "..."
# Usar con autorización del responsable para enviar código de la empresa; los secretos no viajan.
set -euo pipefail

# setx no llega a sesiones ya abiertas: si falta en el entorno, se lee del registro del usuario.
KEY="${DEEPSEEK_API_KEY:-}"
if [[ -z "$KEY" ]] && command -v powershell >/dev/null; then
  KEY=$(powershell -NoProfile -c "[Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY','User')" | tr -d '\r\n')
fi
[[ -z "$KEY" ]] && { echo "DEEPSEEK_API_KEY no está configurada" >&2; exit 3; }

# V4-Pro razona (el antiguo R1 ya no existe en la API); Flash para lo chico (títulos, resúmenes internos de Claude Code).
MODEL="${DS_MODEL:-deepseek-v4-pro}"
MODEL_CHICO="${DS_MODEL_CHICO:-deepseek-flash}"

export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="$KEY"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_FABLE_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_SONNET_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$MODEL_CHICO"
export CLAUDE_CODE_SUBAGENT_MODEL="$MODEL"
# Claude Code no conoce estos modelos y asume 200K; los dos DeepSeek traen 1M.
export CLAUDE_CODE_MAX_CONTEXT_TOKENS="${DS_CONTEXTO:-1048576}"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

echo "Claude Code vía DeepSeek: $MODEL (chico: $MODEL_CHICO)" >&2
exec claude "$@"
