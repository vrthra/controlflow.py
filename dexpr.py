#!/usr/bin/env python3
import string
import ast
import sys
import json
import interp


def levenshtein_delta(s1, s2):
    if len(s1) > len(s2): s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def hamming_delta(s1, s2):
    return sum(e1 != e2 for e1, e2 in zip(s1, s2))

def delta(a, b):
    if type(a) is [int, float] and type(b) is [int, float]: return abs(a - b)
    elif type(a) is str and type(b) is str: return hamming_delta(a, b)
    else: raise Exception('Incorrect Delta  %s : %s' %(a,b))

class DistInterpreter(interp.ExprInterpreter):
    """
    The branch distance evaluator
    """
    def __init__(self, symtable):
        interp.ExprInterpreter.__init__(self, symtable)
        self.unaryop = {
          ast.Invert: lambda a: ~a,
          ast.Not: lambda a: a,
          ast.UAdd: lambda a: +a,
          ast.USub: lambda a: -a
        }

        # cmpop = Eq | NotEq | Lt | LtE | Gt | GtE | Is | IsNot | In | NotIn
        self.cmpop = {

          ast.Eq: lambda a, b: 0 if a == b else delta(a, b),
          ast.NotEq: lambda a, b: 0 if a != b else delta(a, b),

          ast.Lt: lambda a, b: 0 if a < b else delta(a, b),
          ast.LtE: lambda a, b: 0 if a <= b else delta(a, b),
          ast.Gt: lambda a, b: 0 if a > b else delta(a, b),
          ast.GtE: lambda a, b: 0 if a >= b else delta(a, b),

          ast.Is: lambda a, b: a is b,
          ast.IsNot: lambda a, b: a is not b,
          ast.In: lambda a, b: a in b,
          ast.NotIn: lambda a, b: a not in b
        }

        # boolop = And | Or
        self.boolop = {
          ast.And: lambda a, b: a + b,
          ast.Or: lambda a, b: min(a, b)
        }
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
