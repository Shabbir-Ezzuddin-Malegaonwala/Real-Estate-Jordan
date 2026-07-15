"""Safe arithmetic evaluator — the single source of numeric truth.

LLMs are unreliable at arithmetic, so the agent is required to route EVERY
computation (totals, yields, margins, %, unit conversions) through here. We use
numexpr, which parses a restricted math grammar and evaluates it in C — it has
no access to Python builtins, names, attributes, or function calls beyond a
fixed whitelist of math functions. Anything that isn't a pure math expression
is rejected.
"""

from __future__ import annotations

import re

import numexpr as ne

# numexpr already refuses attribute access, imports, and arbitrary calls. We add
# a cheap character gate as defence-in-depth: only maths-shaped input gets in.
_ALLOWED = re.compile(r"^[0-9eE+\-*/%.,()<>=!&|~^ \t]*$")
# A few readable words numexpr supports (functions/operators). Everything else
# alphabetic is rejected so no variable/name resolution can occur.
_ALLOWED_WORDS = {
    "where", "sqrt", "log", "log10", "log1p", "exp", "expm1", "abs", "sin",
    "cos", "tan", "arctan", "sinh", "cosh", "tanh", "floor", "ceil",
}


def calculate(expression: str) -> dict:
    expr = (expression or "").strip()
    if not expr:
        return {"error": "empty_expression", "expression": expression}

    # Strip known words before the character check so e.g. sqrt(2) passes.
    stripped = expr
    for w in _ALLOWED_WORDS:
        stripped = re.sub(rf"\b{w}\b", "", stripped)
    if re.search(r"[A-Za-z_]", stripped):
        return {
            "error": "not_a_pure_math_expression",
            "expression": expression,
            "message": ("Only numeric expressions are allowed (no variable names, "
                        "function calls, or code). Substitute the numbers in first."),
        }
    if not _ALLOWED.match(stripped):
        return {"error": "illegal_characters", "expression": expression}

    try:
        value = ne.evaluate(expr)
        result = value.item() if hasattr(value, "item") else float(value)
    except Exception as e:  # numexpr raises for malformed / unsupported input
        return {"error": "evaluation_failed", "expression": expression, "detail": str(e)}

    if isinstance(result, float):
        result = round(result, 6)
    return {
        "expression": expr,
        "result": result,
        "source": {"name": "calculate tool (numexpr)", "kind": "computation"},
    }
