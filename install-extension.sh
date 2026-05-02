#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$SCRIPT_DIR/vscode-genjin"
EXT_NAME="macrosoft-dev.genjin-lang"

echo "==> Instalando extensão Genjin Language Support..."

# Estratégia 1: vsce package + code --install-extension
if command -v vsce &>/dev/null && command -v code &>/dev/null; then
    echo "    Usando vsce + code CLI"
    VSIX=$(cd "$EXT_DIR" && vsce package --out /tmp/genjin-lang.vsix 2>&1 | tail -1 | awk '{print $NF}')
    code --install-extension /tmp/genjin-lang.vsix
    echo "==> Extensão instalada via vsix."
    exit 0
fi

# Estratégia 2: cópia direta para ~/.vscode/extensions/
if [[ -d "$HOME/.vscode/extensions" ]]; then
    DEST="$HOME/.vscode/extensions/$EXT_NAME"
    echo "    vsce ou code CLI não encontrado — copiando diretamente para $DEST"
    rm -rf "$DEST"
    cp -r "$EXT_DIR" "$DEST"
    echo "==> Extensão instalada em $DEST"
    echo "    Reinicie o VS Code para ativar."
    exit 0
fi

# Estratégia 3: ~/.vscode-server (ambientes remotos / WSL)
if [[ -d "$HOME/.vscode-server/extensions" ]]; then
    DEST="$HOME/.vscode-server/extensions/$EXT_NAME"
    echo "    Detectado ambiente vscode-server — copiando para $DEST"
    rm -rf "$DEST"
    cp -r "$EXT_DIR" "$DEST"
    echo "==> Extensão instalada em $DEST"
    echo "    Reinicie o VS Code Server para ativar."
    exit 0
fi

echo "ERRO: não foi possível localizar o diretório de extensões do VS Code."
echo "      Instale manualmente copiando '$EXT_DIR' para ~/.vscode/extensions/$EXT_NAME"
exit 1
