#!/usr/bin/env python3
import string
import ast
import sys
class ExprInterpreter:
    """
    The meta circular python Exprinterpreter
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

    def parse(self, src):
        """
        >>> i = ExprInterpreter()
        >>> v = i.parse('123')
        >>> v.body[0].value.n
        123
        """
        return ast.parse(src)

    def on_module(self, node):
        """
        Module(stmt* body)
        """
        # return value of module is the last statement
        assert len(node.body) == 1
        return self.ast_eval(node.body[0])

    def on_num(self, node):
        """
        Num(object n) -- a number as a PyObject.
        >>> i = ExprInterpreter()
        >>> i.eval('123')
        123
        """
        return node.n

    def on_assign(self, node):
        """
        Assign(expr* targets, expr value)
        TODO: AugAssign(expr target, operator op, expr value)
        -- 'simple' indicates that we annotate simple name without parens
        TODO: AnnAssign(expr target, expr annotation, expr? value, int simple)
        """
        val = self.ast_eval(node.value)
        if len(node.targets) > 1: raise NotImplemented('Parallel assignments')
        n  = node.targets[0]
        self.symtable[n.id] = val

    def on_nameconstant(self, node):
        """
        NameConstant(singleton value)
        """
        if type(node.value) is bool:
            return 0 if node.value else 1
        return node.value

    def on_name(self, node):
        """
        Name(identifier id, expr_context ctx)
        """
        return self.symtable[node.id]

    def on_expr(self, node):
        """
        Expr(expr value)
        >>> i = ExprInterpreter()
        >>> i.eval('123')
        123
        >>> i.eval('x = 123')
        """
        return self.ast_eval(node.value)

    def ast_eval(self, node):
        if node is None: return
        res = "on_%s" % node.__class__.__name__.lower()
        if hasattr(self, res):
            return getattr(self,res)(node)
        raise Exception('ast_eval: Not Implemented %s' % type(node))


    def on_compare(self, node):
        """
        Compare(expr left, cmpop* ops, expr* comparators)

        >>> i = ExprInterpreter()
        >>> i.eval("2>3")
        False
        >>> i.eval("2<3")
        True
        """
        hd = self.ast_eval(node.left)
        op = node.ops[0]
        tl = self.ast_eval(node.comparators[0])
        return self.OpMap[type(op)](hd, tl)

    def on_unaryop(self, node):
        """
        >>> i = ExprInterpreter()
        >>> i.eval("-2")
        -2
        """
        return self.OpMap[type(node.op)](self.ast_eval(node.operand))


    def on_binop(self, node):
        """
        >>> i = ExprInterpreter()
        >>> i.eval("2+3")
        5
        """
        return self.OpMap[type(node.op)](self.ast_eval(node.left), self.ast_eval(node.right))

    def on_return(self, node):
        self._return = self.ast_eval(node.value)

    def on_if(self, node):
        body = node.body if self.ast_eval(node.test) else node.orelse
        self.body_eval(body)

    def on_call(self, node):
        func = self.ast_eval(node.func)
        args = [self.ast_eval(a) for a in node.args]
        return func(*args)

    def body_eval(self, stmts):
        v = None
        for n in stmts:
            v = self.ast_eval(n)
        return v


    def eval(self, src):
        """
        >>> i = ExprInterpreter()
        >>> i.eval("x=1\\ny=2\\nx")
        1
        >>> i.eval("x = 2+3\\nx")
        5
        """
        try:
            node = self.parse(src)
            return self.ast_eval(node)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    expr = ExprInterpreter(dict(zip(string.ascii_lowercase, range(1,26))))
    v = expr.eval(sys.argv[1])
    print(v)
