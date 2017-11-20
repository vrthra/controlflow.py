#!/usr/bin/env python3
# Author: Rahul Gopinath <rahul.gopinath@cispa.saarland>
# License: GPLv3
"""
PyCFG for Python MCI
"""

__g__ = """
-- ASDL's 7 builtin types are:
-- identifier, int, string, bytes, object, singleton, constant
--
-- singleton: None, True or False
-- constant can be None, whereas None means "no value" for object.

module Python
{
    mod = Module(stmt* body)
        | Interactive(stmt* body)
        | Expression(expr body)

        -- not really an actual node but useful in Jython's typesystem.
        | Suite(stmt* body)

    stmt = FunctionDef(identifier name, arguments args,
                       stmt* body, expr* decorator_list, expr? returns)
          | AsyncFunctionDef(identifier name, arguments args,
                             stmt* body, expr* decorator_list, expr? returns)

          | ClassDef(identifier name,
             expr* bases,
             keyword* keywords,
             stmt* body,
             expr* decorator_list)
          | Return(expr? value)

          | Delete(expr* targets)
          | Assign(expr* targets, expr value)
          | AugAssign(expr target, operator op, expr value)
          -- 'simple' indicates that we annotate simple name without parens
          | AnnAssign(expr target, expr annotation, expr? value, int simple)

          -- use 'orelse' because else is a keyword in target languages
          | For(expr target, expr iter, stmt* body, stmt* orelse)
          | AsyncFor(expr target, expr iter, stmt* body, stmt* orelse)
          | While(expr test, stmt* body, stmt* orelse)
          | If(expr test, stmt* body, stmt* orelse)
          | With(withitem* items, stmt* body)
          | AsyncWith(withitem* items, stmt* body)

          | Raise(expr? exc, expr? cause)
          | Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
          | Assert(expr test, expr? msg)

          | Import(alias* names)
          | ImportFrom(identifier? module, alias* names, int? level)

          | Global(identifier* names)
          | Nonlocal(identifier* names)
          | Expr(expr value)
          | Pass | Break | Continue

          -- XXX Jython will be different
          -- col_offset is the byte offset in the utf8 string the parser uses
          attributes (int lineno, int col_offset)

          -- BoolOp() can use left & right?
    expr = BoolOp(boolop op, expr* values)
         | BinOp(expr left, operator op, expr right)
         | UnaryOp(unaryop op, expr operand)
         | Lambda(arguments args, expr body)
         | IfExp(expr test, expr body, expr orelse)
         | Dict(expr* keys, expr* values)
         | Set(expr* elts)
         | ListComp(expr elt, comprehension* generators)
         | SetComp(expr elt, comprehension* generators)
         | DictComp(expr key, expr value, comprehension* generators)
         | GeneratorExp(expr elt, comprehension* generators)
         -- the grammar constrains where yield expressions can occur
         | Await(expr value)
         | Yield(expr? value)
         | YieldFrom(expr value)
         -- need sequences for compare to distinguish between
         -- x < 4 < 3 and (x < 4) < 3
         | Compare(expr left, cmpop* ops, expr* comparators)
         | Call(expr func, expr* args, keyword* keywords)
         | Num(object n) -- a number as a PyObject.
         | Str(string s) -- need to specify raw, unicode, etc?
         | FormattedValue(expr value, int? conversion, expr? format_spec)
         | JoinedStr(expr* values)
         | Bytes(bytes s)
         | NameConstant(singleton value)
         | Ellipsis
         | Constant(constant value)

         -- the following expression can appear in assignment context
         | Attribute(expr value, identifier attr, expr_context ctx)
         | Subscript(expr value, slice slice, expr_context ctx)
         | Starred(expr value, expr_context ctx)
         | Name(identifier id, expr_context ctx)
         | List(expr* elts, expr_context ctx)
         | Tuple(expr* elts, expr_context ctx)

          -- col_offset is the byte offset in the utf8 string the parser uses
          attributes (int lineno, int col_offset)

    expr_context = Load | Store | Del | AugLoad | AugStore | Param

    slice = Slice(expr? lower, expr? upper, expr? step)
          | ExtSlice(slice* dims)
          | Index(expr value)

    boolop = And | Or

    operator = Add | Sub | Mult | MatMult | Div | Mod | Pow | LShift
                 | RShift | BitOr | BitXor | BitAnd | FloorDiv

    unaryop = Invert | Not | UAdd | USub

    cmpop = Eq | NotEq | Lt | LtE | Gt | GtE | Is | IsNot | In | NotIn

    comprehension = (expr target, expr iter, expr* ifs, int is_async)

    excepthandler = ExceptHandler(expr? type, identifier? name, stmt* body)
                    attributes (int lineno, int col_offset)

    arguments = (arg* args, arg? vararg, arg* kwonlyargs, expr* kw_defaults,
                 arg? kwarg, expr* defaults)

    arg = (identifier arg, expr? annotation)
           attributes (int lineno, int col_offset)

    -- keyword arguments supplied to call (NULL identifier for **kwargs)
    keyword = (identifier? arg, expr value)

    -- import name with optional 'as' alias.
    alias = (identifier name, identifier? asname)

    withitem = (expr context_expr, expr? optional_vars)
}
"""

import ast
import sys
import operator
import json
import astunparse

class CFGNode(dict):
    registry = 1
    cache = {}
    def __init__(self, parents=[], ast=None):
        self.parents = [p.rid for p in parents]
        self.children = []
        self.ast_node = ast
        self.rid  = CFGNode.registry
        self.calls = None
        CFGNode.registry += 1
        CFGNode.cache[self.rid] = self

    @classmethod
    def i(cls, i):
        return cls.cache[i]

    def __str__(self):
        return "id:%d parents: %s src[%d]: %s" % (self.rid, str(self.parents), self.ast_node.lineno, astunparse.unparse(self.ast_node).strip())

    def __repr__(self):
        return str(self)

    def add_from(self, g):
        self.parents.extend([g.rid for g in g])

    def set_calls(self, func):
        self.calls = func

    def to_json(self):
        return {'id':self.rid, 'parents': self.parents, 'calls': self.calls, 'at':self.ast_node.lineno ,'ast':astunparse.unparse(self.ast_node).strip()}

    def to_jsonx(self):
        return {'id':self.rid, 'parents': [CFGNode.cache[p].to_jsonx() for p in self.parents], 'calls':self.calls, 'at':self.ast_node.lineno, 'ast':astunparse.unparse(self.ast_node).strip()}

class PyCFG:
    """
    The python CFG
    """
    def __init__(self):
        self.graph = [] # sentinel

    def parse(self, src):
        return ast.parse(src)

    def walk(self, node, graph):
        if node is None: return
        res = "on_%s" % node.__class__.__name__.lower()
        if hasattr(self, res):
            v = getattr(self,res)
            return v(node, graph)
        else:
            return graph

    def on_module(self, node, graph):
        """
        Module(stmt* body)
        """
        # each time a statement is executed unconditionally, make a link from
        # the result to next statement
        g = graph
        for n in node.body:
            g = self.walk(n, g)
        return g

    def on_assign(self, node, graph):
        """
        Assign(expr* targets, expr value)
        TODO: AugAssign(expr target, operator op, expr value)
        -- 'simple' indicates that we annotate simple name without parens
        TODO: AnnAssign(expr target, expr annotation, expr? value, int simple)
        """
        graph = [CFGNode(parents=graph, ast=node)]
        if len(node.targets) > 1: raise NotImplemented('Parallel assignments')
        return graph

    def on_return(self, node, graph):
        graph = [CFGNode(parents=graph, ast=node)]
        return graph

    def on_break(self, node, graph):
        parent = graph[0].parents[0]
        while not hasattr(CFGNode.i(parent), 'exit_node'):
            # we have ordered parents
            parent, = CFGNode.i(parent).parents

        assert hasattr(CFGNode.i(parent), 'exit_node')
        graph = [CFGNode(parents=graph, ast=node)]

        # make the break one of the parents of label node.
        CFGNode.i(parent).exit_node.add_from(graph)
        return graph

    def on_continue(self, node, graph):
        parent, = graph[0].parents
        while not hasattr(CFGNode.i(parent), 'exit_node'):
            # we have ordered parents
            parent, = CFGNode[parent].parents
        assert hasattr(CFGNode.i(parent), 'exit_node')
        graph = [CFGNode(parents=graph, ast=node)]

        # make continue one of the parents of the original test node.
        CFGNode.i(parent).add_from(graph)
        return graph

    def on_while(self, node, graph):
        # For a while, the earliest parent is the node.test
        test_node = CFGNode(parents=graph, ast=node.test)
        graph = [test_node]

        # This is the exit node for the while loop.
        # TODO: set the location to be last line of the while.
        exit_node = CFGNode(parents=graph, ast=ast.copy_location(ast.parse('pass').body[0], node))

        # we attach the label node here so that break can find it.
        test_node.exit_node = exit_node

        # now we evaluate the body, one at a time.
        g1 = graph
        for n in node.body:
            g1 = self.walk(n, g1)

        # the test node is looped back at the end of processing.
        test_node.add_from(g1)

        # link label node back to the condition.
        exit_node.add_from(graph)
        return [exit_node]

    def on_if(self, node, graph):
        graph = [CFGNode(parents=graph, ast=node.test)]
        g1 = graph
        for n in node.body:
            g1 = self.walk(n, g1)
        g2 = graph
        for n in node.orelse:
            g2 = self.walk(n, g2)
        return g1+g2

    def on_call(self, node, graph):
        #graph = [CFGNode(parents=graph, ast=node)]
        for g in graph:
            g.set_calls(node.func.id)
        return graph

    def on_expr(self, node, graph):
        graph = [CFGNode(parents=graph, ast=node)]
        return self.walk(node.value, graph)

    def gen_cfg(self, src):
        """
        >>> i = PyCFG()
        >>> i.walk("100")
        5
        """
        #try:
        node = self.parse(src)
        return self.walk(node, self.graph)
        #except Exception as e:
        #    print(e)


if __name__ == '__main__':
    def fetch_src(dt):
        return ''.join([e.source for es in dt for e in es.examples])
    import doctest, pudb
    finder = doctest.DocTestFinder()
    src = fetch_src(finder.find(PyCFG.gen_cfg))
    print("from pycfg import *\nimport pudb\npudb.set_trace()\n" + src)
