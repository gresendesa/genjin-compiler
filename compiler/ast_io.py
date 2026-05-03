"""
Serialização e desserialização da AST do compilador Genjin.

Formatos:
  - tokens: lista de dicts  {"type": str, "value": str, "line": int}
  - AST:    dict recursivo  {"__type__": NomeDoNo, ...campos...}

Funções públicas:
  tokens_to_json(tokens)     -> str
  tokens_from_json(s)        -> list[Token]
  ast_to_json(node)          -> str
  ast_from_json(s)           -> ProgramNode
"""

from __future__ import annotations

import json
from typing import Any

from compiler.scanner import Token, TokenType
from compiler.parser import (
    ArgNode, OutputCodeNode, ParamDeclNode, ProcDeclNode, ProcBlockNode,
    VarDeclNode, ExecBlockNode, CaseNode, ProgramNode,
    InlineAtomNode, InlineSeqNode,
)


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def tokens_to_json(tokens: list[Token]) -> str:
    data = [{"type": t.type.name, "value": t.value, "line": t.line} for t in tokens]
    return json.dumps(data, ensure_ascii=False, indent=2)


def tokens_from_json(s: str) -> list[Token]:
    data = json.loads(s)
    return [Token(type=TokenType[d["type"]], value=d["value"], line=d["line"]) for d in data]


# ---------------------------------------------------------------------------
# AST → JSON
# ---------------------------------------------------------------------------

def ast_to_json(node: ProgramNode) -> str:
    return json.dumps(_node_to_dict(node), ensure_ascii=False, indent=2)


def _node_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_node_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _node_to_dict(v) for k, v in obj.items()}

    # Dataclass AST node
    cls = type(obj)
    result: dict[str, Any] = {"__type__": cls.__name__}
    for fname, fval in obj.__dict__.items():
        result[fname] = _node_to_dict(fval)
    return result


# ---------------------------------------------------------------------------
# JSON → AST
# ---------------------------------------------------------------------------

def ast_from_json(s: str) -> ProgramNode:
    data = json.loads(s)
    node = _dict_to_node(data)
    if not isinstance(node, ProgramNode):
        raise ValueError(f"Raiz esperada: ProgramNode, obtido: {type(node).__name__}")
    return node


_NODE_TYPES: dict[str, type] = {
    "ArgNode":        ArgNode,
    "OutputCodeNode": OutputCodeNode,
    "ParamDeclNode":  ParamDeclNode,
    "ProcDeclNode":   ProcDeclNode,
    "ProcBlockNode":  ProcBlockNode,
    "VarDeclNode":    VarDeclNode,
    "ExecBlockNode":  ExecBlockNode,
    "CaseNode":       CaseNode,
    "ProgramNode":    ProgramNode,
}


def _dict_to_node(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_dict_to_node(item) for item in obj]
    if isinstance(obj, dict):
        type_name = obj.get("__type__")
        if type_name is None:
            # dict puro (kwargs de ArgNode)
            return {k: _dict_to_node(v) for k, v in obj.items() if k != "__type__"}
        cls = _NODE_TYPES.get(type_name)
        if cls is None:
            raise ValueError(f"Tipo de nó desconhecido: {type_name!r}")
        fields = {k: _dict_to_node(v) for k, v in obj.items() if k != "__type__"}
        return cls(**fields)
    return obj
