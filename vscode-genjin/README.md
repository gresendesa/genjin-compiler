# Genjin Language Support — VS Code Extension

Extensão para o VS Code que adiciona suporte básico à linguagem **Genjin** (`.gnj` / `.genjin`).

## Funcionalidades

- Reconhecimento de arquivos `.gnj` e `.genjin` como linguagem Genjin
- Syntax highlighting via TextMate Grammar cobrindo:
  - Keywords: `program`, `vars`, `procs`, `proc`, `from`, `exec`, `case`, `pass`, `while`, `as`, `codes`
  - Tipos primitivos: `Number`, `Text`, `Logic`
  - Literais: strings (`"..."`), números inteiros
  - Códigos de saída: `NOME<numero>` (ex: `OK<0>`, `ERROR<1>`)
  - Operador de atribuição de resultado: `>>`
  - Referência por ponteiro: `&`
- Configuração de linguagem:
  - Comentário de linha: `//`
  - Comentário de bloco: `/* */`
  - Auto-closing para `{}`, `()`, `[]`, `""`, `/* */`
  - Indentação automática com `{}`

## Como instalar localmente (modo desenvolvimento)

1. Abra a pasta `vscode-genjin/` no VS Code:
   ```bash
   code vscode-genjin/
   ```
2. Pressione **F5** para abrir o *Extension Development Host*
3. Abra qualquer arquivo `.gnj` ou `.genjin` para ver o highlighting em ação

## Como instalar via `.vsix`

1. Instale o `vsce`:
   ```bash
   npm install -g @vscode/vsce
   ```
2. Empacote a extensão:
   ```bash
   cd vscode-genjin
   vsce package
   ```
3. No VS Code, vá em **Extensions → Install from VSIX...** e selecione o arquivo gerado

## Estrutura do projeto

```
vscode-genjin/
├── package.json                  # Manifesto da extensão
├── language-configuration.json   # Brackets, comentários, auto-close
├── syntaxes/
│   └── genjin.tmLanguage.json    # TextMate Grammar (syntax highlighting)
└── README.md                     # Este arquivo
```

## Evolução futura

A estrutura está preparada para evoluir para:

- `server/` — Language Server (Python via `pygls` ou Node.js)
- `client/` — Cliente LSP integrado ao VS Code
- Autocomplete de keywords, tipos e procedimentos
- Diagnostics em tempo real (erros de sintaxe)
- Hover documentation

## Exemplo de código Genjin

```genjin
program "Sistema de Pagamento"

vars {
    status_var: Number
    res: Text
}

procs {
    proc verificar_rede() from "Net.check" {
        codes ONLINE<0>, OFFLINE<1>
    }
}

exec verificar_rede() >> status_var {
    case OFFLINE: exec verificar_rede() {
        pass ONLINE
    }
    pass ONLINE
}
```
