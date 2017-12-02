#!/usr/bin/env python3
import string
import ast
import astunparse
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
    if type(a) in [int, float] and type(b) in [int, float]: return abs(a - b)
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
          #ast.Not: lambda a: a,
          ast.UAdd: lambda a: +a,
          ast.USub: lambda a: -a
        }

        # cmpop = Eq | NotEq | Lt | LtE | Gt | GtE | Is | IsNot | In | NotIn
        self.cmpop = {

          ast.Eq: lambda a, b: 0 if a == b else delta(a, b) + 1,
          ast.NotEq: lambda a, b: 0 if a != b else 1,

          ast.Lt: lambda a, b: 0 if a < b else delta(a, b) + 1,
          ast.LtE: lambda a, b: 0 if a <= b else delta(a, b) + 1,
          ast.Gt: lambda a, b: 0 if a > b else delta(a, b) + 1,
          ast.GtE: lambda a, b: 0 if a >= b else delta(a, b) + 1,

          ast.Is: lambda a, b: 0 if a is b else 1,
          ast.IsNot: lambda a, b: 0 if a is not b else 1,
          ast.In: lambda a, b: 0 if  a in b else len(b),
          ast.NotIn: lambda a, b: 0 if a not in b else len(b)
        }

        # boolop = And | Or
        self.boolop = {
          ast.And: lambda a, b: a + b,
          ast.Or: lambda a, b: min(a, b)
        }

    def on_nameconstant(self, node):
        """
        Boolean true? 0 : 1
        """
        if type(node.value) is bool:
            return 0 if node.value else 1
        return node.value

    def on_expr(self, node):
        return self.walk(self.dtrans(node.value))

    def dtrans(self, node):
        if type(node) is ast.UnaryOp:
            if type(node.op) is ast.Not:
                return self.not_node(node.operand)
            else:
                # recursion ends here.
                return node
        if type(node) is ast.Compare: # eq lt gt
            # recursion ends here.
            # we dont expect a boolean not inside an arithmetic expression
            return node
        elif type(node) is ast.BoolOp: # and or
            # recursion on the operands
            values = [self.dtrans(i) for i in node.values]
            node.values = values
            return node
        # no more recursion
        return node

    def not_node(self, node):
        if type(node) is ast.UnaryOp and type(node.op) is ast.Not:
            # unwrap it once. not not x == x
            return self.dtrans(node.operand)
        elif type(node) is ast.Compare:
            # arithmetic not a = b == a!= b  eq lt gt
            # no recursion on the operands
            node.ops = [self.not_cmp_trans(node.ops[0])]
            return node
        elif type(node) is ast.BoolOp:
            values = [self.dtrans(i) for i in node.values]
            left, op, right = self.not_bool_trans(values[0], node.op, values[1])
            node.values = [left, right]
            node.op = op
            return node
        else:
            raise Exception('Not not applicable %s' % astunparse.unparse(node))

    def not_cmp_trans(self, op):
        trans=dict([(ast.Eq,ast.Eq()),(ast.NotEq,ast.NotEq()),(ast.Lt,ast.Lt()),(ast.Gt,ast.Gt()),(ast.LtE,ast.LtE()),(ast.GtE,ast.GtE()),(ast.In,ast.In()),(ast.NotIn,ast.NotIn())])
        v = [(ast.Eq, ast.NotEq), (ast.Lt, ast.GtE), (ast.Gt, ast.LtE), (ast.Is, ast.IsNot), (ast.In, ast.NotIn)]
        vv = v + [(j,i) for (i,j) in v]
        d = dict(vv)
        return trans[d[type(op)]]

    def not_bool_trans(self, a, op, b):
        if type(op) == ast.And:
            op = ast.Or()
        elif type(op) == ast.Or:
            op = ast.And()
        return (self.not_node(a), op, self.not_node(b))

if __name__ == '__main__':
    expr = DistInterpreter(json.loads(sys.argv[2]))
    v = expr.eval(sys.argv[1])
    print(v)
