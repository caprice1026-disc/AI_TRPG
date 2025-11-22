import random
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


class DiceError(ValueError):
    # ダイス式のパースや評価で問題があった場合に送出
    pass


@dataclass
class EvalResult:
    total: int
    breakdown: str
    rolls: List[dict]


TOKEN_RE = re.compile(
    r"\s*(adv|dis|\d+d\d+(?:k[hl]\d+)?|d\d+(?:k[hl]\d+)?|[0-9]+|[()+\-*/])",
    re.IGNORECASE,
)


def _tokens(expr: str) -> List[str]:
    # ダイス式をトークン分割
    tokens: List[str] = []
    idx = 0
    while idx < len(expr):
        match = TOKEN_RE.match(expr, idx)
        if not match:
            raise DiceError(f"Invalid token near: {expr[idx:idx+10]}")
        token = match.group(1)
        tokens.append(token)
        idx = match.end()
    return tokens


class _Parser:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Optional[str]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self) -> str:
        tok = self._peek()
        if tok is None:
            raise DiceError("Unexpected end of expression")
        self.pos += 1
        return tok

    def parse(self):
        # トップレベルの式を解析
        node = self._expr()
        if self._peek() is not None:
            raise DiceError(f"Unexpected token: {self._peek()}")
        return node

    def _expr(self):
        node = self._term()
        while self._peek() in ("+", "-"):
            op = self._consume()
            right = self._term()
            node = ("binop", op, node, right)
        return node

    def _term(self):
        node = self._factor()
        while self._peek() in ("*", "/"):
            op = self._consume()
            right = self._factor()
            node = ("binop", op, node, right)
        return node

    def _factor(self):
        tok = self._peek()
        if tok in ("adv", "dis"):
            func = self._consume().lower()
            if self._consume() != "(":
                raise DiceError(f"{func} expects '('")
            expr_node = self._expr()
            if self._consume() != ")":
                raise DiceError(f"{func} expects ')'")
            return ("adv", func, expr_node)
        if tok == "(":
            self._consume()
            node = self._expr()
            if self._consume() != ")":
                raise DiceError("Missing ')'")
            return node
        if tok and re.fullmatch(r"\d*d\d+(?:k[hl]\d+)?", tok, re.IGNORECASE):
            self._consume()
            return ("dice", tok.lower())
        if tok and tok.isdigit():
            self._consume()
            return ("num", int(tok))
        raise DiceError(f"Unexpected token: {tok}")


def _eval(node, rng: random.Random) -> EvalResult:
    ntype = node[0]
    if ntype == "num":
        return EvalResult(total=node[1], breakdown=str(node[1]), rolls=[])
    if ntype == "dice":
        return _eval_dice(node[1], rng)
    if ntype == "binop":
        _, op, left_node, right_node = node
        left = _eval(left_node, rng)
        right = _eval(right_node, rng)
        if op == "+":
            total = left.total + right.total
        elif op == "-":
            total = left.total - right.total
        elif op == "*":
            total = left.total * right.total
        elif op == "/":
            total = int(left.total / right.total)
        else:
            raise DiceError(f"Unsupported op: {op}")
        breakdown = f"({left.breakdown} {op} {right.breakdown})"
        return EvalResult(
            total=total,
            breakdown=breakdown,
            rolls=left.rolls + right.rolls,
        )
    if ntype == "adv":
        _, mode, expr_node = node
        first = _eval(expr_node, rng)
        second = _eval(expr_node, rng)
        chosen, other = (first, second) if first.total >= second.total else (second, first)
        if mode == "dis":
            chosen, other = other, chosen
        breakdown = (
            f"{mode}([{first.breakdown}={first.total}], "
            f"[{second.breakdown}={second.total}]) -> kept {chosen.total}"
        )
        rolls = first.rolls + second.rolls + [
            {"type": mode, "kept": chosen.total, "other": other.total}
        ]
        return EvalResult(total=chosen.total, breakdown=breakdown, rolls=rolls)
    raise DiceError(f"Bad node: {node}")


def _eval_dice(token: str, rng: random.Random) -> EvalResult:
    match = re.fullmatch(r"(?:(\d+)d(\d+)|d(\d+))(?:k([hl])(\d+))?", token)
    if not match:
        raise DiceError(f"Invalid dice token: {token}")
    count = int(match.group(1) or 1)
    sides = int(match.group(2) or match.group(3))
    keep_mode = match.group(4)
    keep_n = int(match.group(5) or 0) if keep_mode else None
    rolls = [rng.randint(1, sides) for _ in range(count)]
    kept = list(rolls)
    if keep_mode:
        reverse = keep_mode == "h"
        kept = sorted(rolls, reverse=reverse)[: keep_n or count]
    total = sum(kept)
    detail = {
        "type": "dice",
        "notation": token,
        "count": count,
        "sides": sides,
        "rolls": rolls,
        "kept": kept,
        "total": total,
    }
    breakdown = f"{token} -> {rolls}"
    if keep_mode:
        breakdown += f" kept {kept}"
    return EvalResult(total=total, breakdown=breakdown, rolls=[detail])


def roll(expression: str, rng: Optional[random.Random] = None) -> dict:
    """ダイス式を評価して合計と出目詳細を返す。"""
    rng = rng or random.Random()
    tokens = _tokens(expression)
    parser = _Parser(tokens)
    ast = parser.parse()
    result = _eval(ast, rng)
    return {
        "expression": expression,
        "total": result.total,
        "breakdown": result.breakdown,
        "rolls": result.rolls,
    }
