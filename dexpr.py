#!/usr/bin/env python3
import string
import ast
import sys
import json
import interp
class DistInterpreter(interp.ExprInterpreter):
    """
    The branch distance evaluator
    """
    def __init__(self, symtable):
        self.OpMap = {
          ast.Is: lambda a, b: a is b,
          ast.IsNot: lambda a, b: a is not b,
          ast.In: lambda a, b: a in b,
          ast.NotIn: lambda a, b: a not in b,
          ast.Add: lambda a, b: a + b,
          ast.BitAnd: lambda a, b: a & b,
          ast.BitOr: lambda a, b: a | b,
          ast.BitXor: lambda a, b: a ^ b,
          ast.Div: lambda a, b: a / b,
          ast.FloorDiv: lambda a, b: a // b,
          ast.LShift:  lambda a, b: a << b,
          ast.RShift: lambda a, b: a >> b,
          ast.Mult:  lambda a, b: a * b,
          ast.Pow: lambda a, b: a ** b,
          ast.Sub: lambda a, b: a - b,
          ast.Mod: lambda a, b: a % b,

          ast.And: lambda a, b: a + b,
          ast.Or: lambda a, b: min(a, b),

          ast.Eq: lambda a, b: 0 if abs(a - b) == 0 else abs(a - b),
          ast.Gt: lambda a, b: 0 if abs(a - b) > 0 else abs(a - b),
          ast.GtE: lambda a, b: 0 if abs(a - b) >= 0 else abs(a - b),
          ast.Lt: lambda a, b: 0 if abs(a - b) < 0 else abs(a - b),
          ast.LtE: lambda a, b: 0 if abs(a - b) <= 0 else abs(a - b),
          ast.NotEq: lambda a, b: 0 if abs(a - b) != 0 else abs(a - b),

          ast.Invert: lambda a: ~a,

          ast.Not: lambda a: a,

          ast.UAdd: lambda a: +a,
          ast.USub: lambda a: -a}
        self.symtable = symtable

    def on_nameconstant(self, node):
        """
        Boolean true? 0 : 1
        """
        if type(node.value) is bool:
            return 0 if node.value else 1
        return node.value

if __name__ == '__main__':
    expr = DistInterpreter(json.loads(sys.argv[2]))
    v = expr.eval(sys.argv[1])
    print(v)
