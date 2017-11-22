#!/usr/bin/env python3
# Author: Rahul Gopinath <rahul.gopinath@cispa.saarland>
# License: GPLv3
"""
PyCFG for Python MCI
Use http://viz-js.com/ to view digraph output
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
import pygraphviz
import argparse

class CFGNode(dict):
    registry = 0
    cache = {}
    stack = []
    def __init__(self, parent=None, ast=None):
        if parent is not None:
            assert type(parent) is CFGNode
            self.parents = [parent.rid]
        else:
            self.parents = []
        self.calls = []
        self.children = []
        self.ast_node = ast
        self.rid  = CFGNode.registry
        CFGNode.cache[self.rid] = self
        CFGNode.registry += 1

    @classmethod
    def i(cls, i):
        return cls.cache[i]

    def __str__(self):
        lineno = self.ast_node.lineno if hasattr(self.ast_node, 'lineno') else 0
        return "id:%d parents: %s src[%d]: %s" % (self.rid, str(self.parents), lineno, astunparse.unparse(self.ast_node).strip())

    def __repr__(self):
        return str(self)

    def add_child(self, c):
        assert type(c) is int
        if c not in self.children:
            self.children.append(c)

    def add_parent(self, p):
        assert type(p) is CFGNode
        if p not in self.parents:
            self.parents.append(p.rid)

    def add_parents(self, ps):
        assert type(p) is CFGNode
        for p in ps:
            self.add_parent(p.rid)

    def add_calls(self, func):
        self.calls.append(func)

    def to_json(self):
        lineno = self.ast_node.lineno if hasattr(self.ast_node, 'lineno') else 0
        return {'id':self.rid, 'parents': self.parents, 'children': self.children, 'calls': self.calls, 'at':lineno ,'ast':astunparse.unparse(self.ast_node).strip()}

    @classmethod
    def to_dot(cls):
        G = pygraphviz.AGraph(directed=True)
        for k, v in CFGNode.cache.items():
            G.add_node(k)
            n = G.get_node(k)
            cnode = CFGNode.i(k)
            lineno = cnode.ast_node.lineno if hasattr(cnode.ast_node, 'lineno') else 0
            n.attr['label'] = "%d: %s" % (lineno, astunparse.unparse(cnode.ast_node).strip())
            if cnode.parents:
                for i in cnode.parents:
                    G.add_edge(i, k)
        return G.string()
class PyCFG:
    """
    The python CFG
    """
    def __init__(self):
        self.founder = CFGNode(parent=None, ast=ast.parse('start()').body[0]) # sentinel
        self.functions = {}

    def parse(self, src):
        return ast.parse(src)

    def walk(self, node, myparent):
        if node is None: return
        fname = "on_%s" % node.__class__.__name__.lower()
        if hasattr(self, fname):
            fn = getattr(self, fname)
            return fn(node, myparent)
        else:
            return myparent

    def on_module(self, node, myparent):
        """
        Module(stmt* body)
        """
        # each time a statement is executed unconditionally, make a link from
        # the result to next statement
        p = myparent
        for n in node.body:
            p = self.walk(n, p)
        return p

    def on_assign(self, node, myparent):
        """
        Assign(expr* targets, expr value)
        TODO: AugAssign(expr target, operator op, expr value)
        -- 'simple' indicates that we annotate simple name without parens
        TODO: AnnAssign(expr target, expr annotation, expr? value, int simple)
        """
        if len(node.targets) > 1: raise NotImplemented('Parallel assignments')

        return CFGNode(parent=myparent, ast=node)

    def on_return(self, node, myparent):
        return CFGNode(parent=myparent, ast=node)

    def on_break(self, node, myparent):
        parent = myparent.parents[0]
        while not hasattr(CFGNode.i(parent), 'exit_node'):
            # we have ordered parents
            parent = CFGNode.i(parent).parents[0]

        assert hasattr(CFGNode.i(parent), 'exit_node')
        p = CFGNode(parent=myparent, ast=node)

        # make the break one of the parents of label node.
        CFGNode.i(parent).exit_node.add_parent(p)

        return myparent

    def on_continue(self, node, myparent):
        parent = myparent.parents[0]
        while not hasattr(CFGNode.i(parent), 'exit_node'):
            # we have ordered parents
            parent = CFGNode.i(parent).parents[0]
        assert hasattr(CFGNode.i(parent), 'exit_node')
        p = CFGNode(parent=myparent, ast=node)

        # make continue one of the parents of the original test node.
        CFGNode.i(parent).add_parent(p)
        # return the parent because a continue is not the parent
        # for the just next node
        return myparent

    def on_for(self, node, myparent):
        #node.target in node.iter: node.body
        test_node = CFGNode(parent=myparent, ast=ast.parse('for_enter: True if %s else False' % astunparse.unparse(node.iter).strip()).body[0])
        ast.copy_location(test_node, node)

        # This is the exit node for the while loop.
        exit_node = CFGNode(parent=test_node, ast=ast.parse('for_exit').body[0])

        # we attach the label node here so that break can find it.
        test_node.exit_node = exit_node

        extract_node = CFGNode(parent=test_node, ast=ast.parse('%s = %s.shift()' % (astunparse.unparse(node.target).strip(), astunparse.unparse(node.iter).strip())).body[0])
        ast.copy_location(extract_node.ast_node, test_node.ast_node)

        # now we evaluate the body, one at a time.
        p1 = extract_node
        for n in node.body:
            p1 = self.walk(n, p1)

        # the test node is looped back at the end of processing.
        test_node.add_parent(p1)

        # link label node back to the condition.
        exit_node.add_parent(test_node)
        # exit_node.add_parent(p1) -- the previous node is not a condition node.
        ast.copy_location(exit_node.ast_node, node.body[-1])
        return exit_node


    def on_while(self, node, myparent):
        # For a while, the earliest parent is the node.test
        test_node = CFGNode(parent=myparent, ast=ast.parse('while_enter: %s' % astunparse.unparse(node.test).strip()).body[0])
        ast.copy_location(test_node.ast_node, node.test)
        test_node = self.walk(node.test, test_node)

        # This is the exit node for the while loop.
        exit_node = CFGNode(parent=test_node, ast=ast.parse('while_exit').body[0])

        # we attach the label node here so that break can find it.
        test_node.exit_node = exit_node

        # now we evaluate the body, one at a time.
        p1 = test_node
        for n in node.body:
            p1 = self.walk(n, p1)

        # the test node is looped back at the end of processing.
        test_node.add_parent(p1)

        # link label node back to the condition.
        exit_node.add_parent(test_node)
        #exit_node.add_parent(p1) -- the previous node is not a condition node
        ast.copy_location(exit_node.ast_node, node.body[-1])
        return exit_node

    def on_if(self, node, myparent):
        myparent = CFGNode(parent=myparent, ast=ast.parse('if_enter: %s' % astunparse.unparse(node.test).strip()).body[0])
        ast.copy_location(myparent.ast_node, node.test)
        g1 = myparent
        for n in node.body:
            g1 = self.walk(n, g1)
        g2 = myparent
        for n in node.orelse:
            g2 = self.walk(n, g2)

        # add a dummy
        last_body = node.orelse if node.orelse else node.body
        exit_node = CFGNode(parent=g1, ast=ast.copy_location(ast.parse('if_exit').body[0], last_body[-1]))
        exit_node.add_parent(g2)
        return exit_node

    def on_binop(self, node, myparent):
        left = self.walk(node.left, myparent)
        right = self.walk(node.right, left)
        return right

    def on_compare(self, node, myparent):
        left = self.walk(node.left, myparent)
        right = self.walk(node.comparators[0], left)
        return right

    def on_unaryop(self, node, myparent):
        return self.walk(node.operand, myparent)

    def on_call(self, node, myparent):
        p = myparent
        for a in node.args:
            p = self.walk(a, p)
        myparent.add_calls(node.func.id)
        return p

    def on_expr(self, node, myparent):
        p = CFGNode(parent=myparent, ast=node)
        return self.walk(node.value, p)

    def on_functiondef(self, node, myparent):
        # a function definition does not actually continue the thread of
        # control flow
        # name, args, body, decorator_list, returns
        fname = node.name
        args = node.args
        returns = node.returns

        enter_node = CFGNode(parent=None, ast=ast.parse(node.name + '_enter').body[0]) # sentinel
        ast.copy_location(enter_node.ast_node, node)
        exit_node = CFGNode(parent=None, ast=ast.parse(node.name + '_exit').body[0]) # sentinel

        p = enter_node
        for n in node.body:
            p = self.walk(n, p)
        exit_node.add_parent(p)
        ast.copy_location(exit_node.ast_node, node.body[-1])

        self.functions[fname] = [enter_node, exit_node]

        return myparent

    def link_functions(self):
        for k,v in CFGNode.cache.items():
            if v.calls:
                for calls in v.calls:
                    if calls in self.functions:
                        enter, exit = self.functions[calls]
                        enter.add_parent(v)
                        v.add_parent(exit)

    def update_children(self):
        for k,v in CFGNode.cache.items():
            for p in v.parents:
                CFGNode.cache[p].add_child(k)

    def gen_cfg(self, src):
        """
        >>> i = PyCFG()
        >>> i.walk("100")
        5
        """
        node = self.parse(src)
        node = self.walk(node, self.founder)
        self.last_node = CFGNode(parent=node, ast=ast.parse('stop()').body[0])
        ast.copy_location(self.last_node.ast_node, node.ast_node)
        self.update_children()
        self.link_functions()

def slurp(f):
    with open(f, 'r') as f: return f.read()


def get_cfg(pythonfile):
    cfg = PyCFG()
    cfg.gen_cfg(slurp(pythonfile).strip())
    cache = CFGNode.cache
    g = {}
    for k,v in cache.items():
        j = v.to_json()
        at = j['at']
        parents_at = [cache[p].to_json()['at'] for p in j['parents']]
        children_at = [cache[c].to_json()['at'] for c in j['children']]
        if at not in g:
            g[at] = {'parents':set(), 'children':set()}
        # remove dummy nodes
        ps = set([p for p in parents_at if p != at])
        cs = set([c for c in children_at if c != at])
        g[at]['parents'] |= ps
        g[at]['children'] |= cs
    return g

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pythonfile', help='The python file to be analyzed')
    parser.add_argument('-d','--dots', action='store_true', help='generate a dot file')
    parser.add_argument('-c','--cfg', action='store_true', help='print cfg')
    args = parser.parse_args()
    if args.dots:
        cfg = PyCFG()
        cfg.gen_cfg(slurp(args.pythonfile).strip())
        print(CFGNode.to_dot())
    elif args.cfg:
        cfg = get_cfg(args.pythonfile)
        for i in sorted(cfg):
            print(i,'parents:', cfg[i]['parents'], 'children:', cfg[i]['children'])
