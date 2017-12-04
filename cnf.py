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
        self.literals = {}

    def on_expr(self, node):
        not_bottom = self.not_down(node.value)
        rename_clause = self.stdtrans(not_bottom)
        v = self.distribute_and_over_or(rename_clause)
        vx = self.enflatten(v)
        self.get_literals(vx)
        print("literals: %s" % str([s for s in self.literals.keys()]))
        print(astunparse.unparse(vx))

        self.satisfy(vx, self.literals, {})
        return self.walk(v)

    def get_unit_clauses(self, node, guess):
        assert type(node) is ast.BoolOp
        assert type(node.op) is ast.And
        remains = []
        for clause in node.values:
            assert type(clause.op) is ast.Or
            lit = []
            nfalse = 0
            for v in clause.values:
                if v.id[0] == '_':
                    if v.id[1:] not in guess:
                        lit.append((v.id[1:], False))
                    else: # ignore
                        pass
                else:
                    if v.id not in guess:
                        lit.append((v.id, True))
                    else: # ignore
                        pass
            if len(lit) == 1:
                remains.append(lit[0])
        return remains

    def closure(self, node, guess):
        remains = self.get_unit_clauses(node, guess)
        dremains = self.consistent(remains)
        if not dremains: return None
        guess = {**guess, **dremains}
        while remains:
            remains = self.get_unit_clauses(node, guess)
            dremains = self.consistent(remains)
            if not dremains: return None
            guess = {**guess, **dremains}
        return guess

    def consistent(self, vx):
        # ensure that no True/False clash for same literals happen.
        d = {}
        for (k,v) in vx:
            if k in d:
                if d[k] != v: return None
            else:
                d[k] = v
        return d

    def satisfy(self, node, lst, guess):
        def restofit(lst, guess):
            # strip out all guess keys from lst
            return [i for i in lst if i not in guess]

        if not lst: return True
        # guess hd
        hd, *tl = lst
        # can all unit clauses be satisfied?
        guess = {hd: True}
        assignments = self.closure(node, guess)
        # verify clauses
        if not(assignments):
            guess = {hd: False}
            assignments = self.closure(node, guess)
        if not(assignments): return False
        return self.satisfy(node, restofit(lst, assignments.keys()), assignments)



    def get_literals(self, node):
        if type(node) is ast.UnaryOp:
            if type(node.op) is ast.Not:
                self.get_literals(node.operand)
            else:
                raise None
        elif type(node) is ast.Compare:
           raise None
        elif type(node) is ast.BoolOp:
            if type(node.op) in [ast.And, ast.Or]:
                for i in node.values:
                    self.get_literals(i)
        elif type(node) is ast.Name:
            if node.id[0] == '_':
                self.literals[node.id[1:]] = None
            else:
                self.literals[node.id] = None

    def nid(self):
        self._nid += 1
        return self._nid

    def add_cache(self, node, is_not):
        src = astunparse.unparse(node)
        if is_not:
            if src in self.src_cache: return ast.UnaryOp(ast.Not(), self.src_cache[src])
        else:
            if src in self.src_cache: return self.src_cache[src]
        nid = self.nid()
        name = ast.Name('X%d' % self._nid, None)
        self.src_cache[src] = name
        self.nid_cache[nid] = node
        if is_not:
            return ast.Name('_X%d' % self._nid, None)
        else:
            return name


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
                nid = self.add_cache(node, True)
                newnode = ast.UnaryOp(ast.Not(), nid)
                return newnode
            elif type(node.ops[0]) is ast.Gt:
                node.ops[0] = ast.LtE()
                nid = self.add_cache(node, True)
                newnode = ast.UnaryOp(ast.Not(), nid)
                return newnode
            elif type(node.ops[0]) is ast.GtE:
                node.ops[0] = ast.Lt()
                nid = self.add_cache(node, True)
                newnode = ast.UnaryOp(ast.Not(), nid)
                return newnode

            elif type(node.ops[0]) is ast.Eq:
                nid = self.add_cache(node, False)
                return nid
            elif type(node.ops[0]) is ast.Lt:
                nid = self.add_cache(node, False)
                return nid
            elif type(node.ops[0]) is ast.LtE:
                nid = self.add_cache(node, False)
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
