from __future__ import annotations

import ast
import operator
from datetime import datetime, timezone

from langchain_core.tools import tool

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))#先算左子树、再算右子树，最后用运算符合并
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))#算操作数，再取负等  
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value#（常量）→ 直接返回数
    raise ValueError(f"不支持的表达式: {ast.dump(node)}")

@tool
def calculator(expression: str) -> str:
    """计算基础算术表达式（+ - * / ** %），返回结果字符串。"""
    try:
        tree = ast.parse(expression, mode="eval")#解析表达式，生成AST树
        return str(_eval(tree.body))
    except Exception as exc:
        return f"错误：无法计算 '{expression}'：{exc}"

@tool
def get_current_time() -> str:
    """获取当前时间，格式为UTC, ISO 8601 格式。"""
    return datetime.now(timezone.utc).isoformat()

BASIC_TOOLS = [calculator, get_current_time]
