#!/usr/bin/env python3
import string
import functools
import ast
import astunparse
import sys
import json
import interp
import collections


class CNFInterpreter(interp.ExprInterpreter):
    """
    The branch distance evaluator
    """
    def __init__(self, symtable):
        interp.ExprInterpreter.__init__(self, symtable)

        # ignore values for now.
        self.symtable = collections.defaultdict(int)
        self.src_cache = {}
        self.nid_cache = {}
        self._nid = 0

    def on_expr(self, node):
        not_bottom = self.not_down(node.value)
        rename_clause = self.stdtrans(not_bottom)
        v = self.distribute_and_over_or(rename_clause)
        vx = self.enflatten(v)
        print(astunparse.unparse(vx))
        return self.walk(v)

    def nid(self):
        self._nid += 1
        return ast.Name('X%d' % self._nid, None)

    def add_cache(self, node):
        src = astunparse.unparse(node)
        if src in self.src_cache: return self.src_cache[src]
        nid = self.nid()
        self.src_cache[src] = nid
        self.nid_cache[nid] = node
        return nid


    def enflatten(self, node):
        if type(node) is ast.UnaryOp:
            return node
        if type(node) is ast.Compare:
            return node
        if type(node) is ast.BoolOp:
            flat = []
            nnode = [self.enflatten(i) for i in node.values]
            if type(node.op) is ast.And:
                for n in nnode:
                    if type(n) is ast.BoolOp and type(n.op) is ast.And:
                        flat += [self.enflatten(i) for i in n.values]
                    else:
                        flat.append(self.enflatten(n))
                return ast.BoolOp(ast.And(), flat)
            elif type(node.op) is ast.Or:
                for n in nnode:
                    if type(n) is ast.BoolOp and type(n.op) is ast.Or:
                        flat += [self.enflatten(i) for i in n.values]
                    else:
                        flat.append(self.enflatten(n))
                return ast.BoolOp(ast.Or(), flat)
            else: raise Exception('Not Implemented')
        return node

    def distribute_and_over_or(self, node):
        """Given a sentence s consisting of conjunctions and disjunctions
        of literals, return an equivalent sentence in CNF.
        >>> distribute_and_over_or((A & B & D) | C)
        ((A | C) & (B | C) & (D | C))
        """
        def distribute(x, y):
            if type(x) is ast.BoolOp and type(x.op) is ast.And:
                return ast.BoolOp(ast.And(), [self.distribute_and_over_or(ast.BoolOp(ast.Or(), [xi,y])) for xi in x.values])
            elif type(y) is ast.BoolOp and type(y.op) is ast.And:
                return ast.BoolOp(ast.And(), [self.distribute_and_over_or(ast.BoolOp(ast.Or(), [yi,x])) for yi in y.values])
            else: return ast.BoolOp(ast.Or(),[x, y])

        if type(node) is ast.UnaryOp:
            return node
        elif type(node) is ast.Compare:
            return node
        elif type(node) is ast.BoolOp:
            # distribute
            if type(node.op) is ast.Or:
                node = functools.reduce(lambda x, y: distribute(x, y),node.values)
                return node
            elif type(node.op) is ast.And:
                return ast.BoolOp(ast.And(), [self.distribute_and_over_or(i) for i in node.values])
            else: raise Exception('Not Implemented')
        else:
            return node

    def stdtrans(self, node):
        """ convert neq to not eq gt to not lte gte to lt"""
        if type(node) is ast.UnaryOp:
            if type(node.op) is ast.Not:
                node.operand = self.stdtrans(node.operand)
                return node
            else:
                # recursion ends here.
                return node
        if type(node) is ast.Compare: # eq lt gt
            # recursion ends here.
            if type(node.ops[0]) is ast.NotEq:
                node.ops[0] = ast.Eq()
                nid = self.add_cache(node)
                newnode = ast.UnaryOp(ast.Not(), nid)
                return newnode
            elif type(node.ops[0]) is ast.Gt:
                node.ops[0] = ast.LtE()
                nid = self.add_cache(node)
                newnode = ast.UnaryOp(ast.Not(), nid)
                return newnode
            elif type(node.ops[0]) is ast.GtE:
                node.ops[0] = ast.Lt()
                nid = self.add_cache(node)
                newnode = ast.UnaryOp(ast.Not(), nid)
                return newnode

            elif type(node.ops[0]) is ast.Eq:
                nid = self.add_cache(node)
                return nid
            elif type(node.ops[0]) is ast.Lt:
                nid = self.add_cache(node)
                return nid
            elif type(node.ops[0]) is ast.LtE:
                nid = self.add_cache(node)
                return nid
            else:
                return node
        elif type(node) is ast.BoolOp: # and or
            # recursion on the operands
            values = [self.stdtrans(i) for i in node.values]
            node.values = values
            return node
        elif type(node) is ast.Name:
            return node
        elif type(node) is ast.NameConst:
            return node
        else:
            raise 'Not implemented %s' % str(type(node))
        # no more recursion
        return node

    def not_down(self, node):
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
            values = [self.not_down(i) for i in node.values]
            node.values = values
            return node
        # no more recursion
        return node

    def not_node(self, node):
        if type(node) is ast.UnaryOp and type(node.op) is ast.Not:
            # unwrap it once. not not x == x
            return self.not_down(node.operand)
        elif type(node) is ast.Compare:
            # arithmetic not a = b == a!= b  eq lt gt
            # no recursion on the operands
            node.ops = [self.not_cmp_trans(node.ops[0])]
            return node
        elif type(node) is ast.BoolOp:
            values = [self.not_down(i) for i in node.values]
            left, op, right = self.not_bool_trans(values[0], node.op, values[1])
            node.values = [left, right]
            node.op = op
            return node
        else:
            return ast.UnaryOp(ast.Not(), node)

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
    expr = CNFInterpreter(json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
    v = expr.eval(sys.argv[1])
    print(v)

my_ast = ast.parse(sys.argv[1]).body[0]
