#!/usr/bin/env python3
# Author: Rahul Gopinath <rahul.gopinath@cispa.saarland>
# License: GPLv3
"""
PyCFG for Python MCI
Use http://viz-js.com/ to view digraph output
"""

import ast
import re
import astunparse
import pygraphviz

class CFGNode(dict):
    registry = 0
    cache = {}
    stack = []
    def __init__(self, parents=[], ast=None):
        if parents:
            assert type(parents[0]) is CFGNode
        self.parents = [parent.rid for parent in parents]
        self.calls = []
        self.children = []
        self.ast_node = ast
        self.rid  = CFGNode.registry
        CFGNode.cache[self.rid] = self
        CFGNode.registry += 1

    @classmethod
    def i(cls, i):
        return cls.cache[i]

    @classmethod
    def l(cls, i):
        n = cls.i(i)
        return n.ast_node.lineno if hasattr(n.ast_node, 'lineno') else 0

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
        assert type(ps) is list
        for p in ps:
            self.add_parent(p)

    def add_calls(self, func):
        self.calls.append(func)

    def to_json(self):
        lineno = self.ast_node.lineno if hasattr(self.ast_node, 'lineno') else 0
        return {'id':self.rid, 'parents': self.parents, 'children': self.children, 'calls': self.calls, 'at':lineno ,'ast':astunparse.unparse(self.ast_node).strip()}

    @classmethod
    def to_dot(cls, arcs=None):
        def unhack(v):
            for i in ['if', 'while', 'for']:
                v = re.sub(r'^_%s:' % i, '%s:' % i, v)
            return v
        G = pygraphviz.AGraph(directed=True)
        cov_lines = [i for i,j in arcs]
        for k, v in CFGNode.cache.items():
            G.add_node(k)
            n = G.get_node(k)
            cnode = CFGNode.i(k)
            lineno = CFGNode.l(k)
            n.attr['label'] = "%d: %s" % (lineno, unhack(astunparse.unparse(cnode.ast_node).strip()))
            if cnode.parents:
                for i in cnode.parents:
                    plineno = CFGNode.l(i)
                    if  (plineno, lineno) in arcs:
                        G.add_edge(i, k, color='blue')
                    elif plineno == lineno and lineno in cov_lines:
                        G.add_edge(i, k, color='blue')
                    else:
                        G.add_edge(i, k, color='red')
        return G.string()

class PyCFG:
    """
    The python CFG
    """
    def __init__(self):
        self.founder = CFGNode(parents=[], ast=ast.parse('start').body[0]) # sentinel
        self.founder.ast_node.lineno = 0
        self.functions = {}

    def parse(self, src):
        return ast.parse(src)

    def walk(self, node, myparents):
        assert type(myparents[0]) is CFGNode
        if node is None: return
        fname = "on_%s" % node.__class__.__name__.lower()
        if hasattr(self, fname):
            fn = getattr(self, fname)
            assert type(myparents[0]) is CFGNode
            v = fn(node, myparents)
            if v: assert type(v[0]) is CFGNode
            return v
        else:
            return myparents

    def on_module(self, node, myparents):
        """
        Module(stmt* body)
        """
        # each time a statement is executed unconditionally, make a link from
        # the result to next statement
        p = myparents
        for n in node.body:
            p = self.walk(n, p)
        return p

    def on_assign(self, node, myparents):
        """
        Assign(expr* targets, expr value)
        TODO: AugAssign(expr target, operator op, expr value)
        -- 'simple' indicates that we annotate simple name without parens
        TODO: AnnAssign(expr target, expr annotation, expr? value, int simple)
        """
        if len(node.targets) > 1: raise NotImplemented('Parallel assignments')

        return [CFGNode(parents=myparents, ast=node)]

    def on_pass(self, node, myparents):
        assert type(myparents) is list
        assert type(myparents[0]) is CFGNode
        return [CFGNode(parents=myparents, ast=node)]

    def on_break(self, node, myparents):
        parent = myparents[0].parents[0]
        while not hasattr(CFGNode.i(parent), 'exit_nodes'):
            # we have ordered parents
            parent = CFGNode.i(parent).parents[0]

        assert hasattr(CFGNode.i(parent), 'exit_nodes')
        p = CFGNode(parents=myparents, ast=node)

        # make the break one of the parents of label node.
        CFGNode.i(parent).exit_nodes.append(p)

        # break doesnt have immediate children
        return []

    def on_continue(self, node, myparents):
        parent = myparents[0].parents[0]
        while not hasattr(CFGNode.i(parent), 'exit_nodes'):
            # we have ordered parents
            parent = CFGNode.i(parent).parents[0]
        assert hasattr(CFGNode.i(parent), 'exit_nodes')
        p = CFGNode(parents=myparents, ast=node)

        # make continue one of the parents of the original test node.
        CFGNode.i(parent).add_parent(p)

        # return the parent because a continue is not the parent
        # for the just next node
        return []

    def on_for(self, node, myparents):
        #node.target in node.iter: node.body
        _test_node = CFGNode(parents=myparents, ast=ast.parse('_for: True if %s else False' % astunparse.unparse(node.iter).strip()).body[0])
        ast.copy_location(_test_node.ast_node, node)

        # we attach the label node here so that break can find it.
        _test_node.exit_nodes = []
        test_node = self.walk(node.iter, [_test_node])

        extract_node = CFGNode(parents=[_test_node], ast=ast.parse('%s = %s.shift()' % (astunparse.unparse(node.target).strip(), astunparse.unparse(node.iter).strip())).body[0])
        ast.copy_location(extract_node.ast_node, _test_node.ast_node)

        # now we evaluate the body, one at a time.
        p1 = extract_node
        for n in node.body:
            p1 = self.walk(n, p1)

        # the test node is looped back at the end of processing.
        _test_node.add_parent(p1)

        return _test_node.exit_nodes + test_node


    def on_while(self, node, myparents):
        # For a while, the earliest parent is the node.test
        _test_node = CFGNode(parents=myparents, ast=ast.parse('_while: %s' % astunparse.unparse(node.test).strip()).body[0])
        ast.copy_location(_test_node.ast_node, node.test)
        _test_node.exit_nodes = []
        test_node = self.walk(node.test, [_test_node])

        # we attach the label node here so that break can find it.

        # now we evaluate the body, one at a time.
        p1 = test_node
        for n in node.body:
            p1 = self.walk(n, p1)

        # the test node is looped back at the end of processing.
        _test_node.add_parents(p1)

        # link label node back to the condition.
        return _test_node.exit_nodes + test_node

    def on_if(self, node, myparents):
        _test_node = CFGNode(parents=myparents, ast=ast.parse('_if: %s' % astunparse.unparse(node.test).strip()).body[0])
        ast.copy_location(_test_node.ast_node, node.test)
        test_node = self.walk(node.test, [_test_node])
        g1 = test_node
        for n in node.body:
            g1 = self.walk(n, g1)
        assert type(g1) is list
        g2 = test_node
        for n in node.orelse:
            g2 = self.walk(n, g2)
        assert type(g2) is list

        return g1 + g2

    def on_binop(self, node, myparents):
        left = self.walk(node.left, myparents)
        right = self.walk(node.right, left)
        return right

    def on_compare(self, node, myparents):
        left = self.walk(node.left, myparents)
        right = self.walk(node.comparators[0], left)
        return right

    def on_unaryop(self, node, myparents):
        return self.walk(node.operand, myparents)

    def on_call(self, node, myparents):
        p = myparents
        for a in node.args:
            p = self.walk(a, p)
        myparents[0].add_calls(node.func.id)
        return p

    def on_expr(self, node, myparents):
        p = [CFGNode(parents=myparents, ast=node)]
        return self.walk(node.value, p)

    def on_return(self, node, myparents):
        assert type(myparents) is list
        assert type(myparents[0]) is CFGNode
        parent = myparents[0].parents[0]
        # on return look back to the function definition.
        while not hasattr(CFGNode.i(parent), 'return_nodes'):
            parent = CFGNode.i(parent).parents[0]
        assert hasattr(CFGNode.i(parent), 'return_nodes')

        p = CFGNode(parents=myparents, ast=node)

        # make the break one of the parents of label node.
        CFGNode.i(parent).return_nodes.append(p)

        # return doesnt have immediate children
        #return [CFGNode.i(parent)]
        return []

    def on_functiondef(self, node, myparents):
        # a function definition does not actually continue the thread of
        # control flow
        # name, args, body, decorator_list, returns
        fname = node.name
        args = node.args
        returns = node.returns

        enter_node = CFGNode(parents=[], ast=ast.parse('enter: %s(%s)' % (node.name, ', '.join([a.arg for a in node.args.args])) ).body[0]) # sentinel
        ast.copy_location(enter_node.ast_node, node)
        exit_node = CFGNode(parents=[], ast=ast.parse('exit: %s' %node.name).body[0]) # sentinel
        enter_node.return_nodes = [] # sentinel

        p = [enter_node]
        for n in node.body:
            assert type(p[0]) is CFGNode
            p = self.walk(n, p)
            if p: assert type(p[0]) is CFGNode

        ast.copy_location(exit_node.ast_node, node.body[-1])

        # we assume that the function has at least one return statement.
        #if enter_node.return_nodes:
        exit_node.add_parents(enter_node.return_nodes)
        #else:
        #    exit_node.add_parents(p)

        self.functions[fname] = [enter_node, exit_node]

        return myparents

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
        nodes = self.walk(node, [self.founder])
        self.last_node = CFGNode(parents=nodes, ast=ast.parse('stop').body[0])
        ast.copy_location(self.last_node.ast_node, node.body[-1])
        self.update_children()
        self.link_functions()

def compute_dominator(cfg, start = 0, key='parents'):
    dominator = {}
    dominator[start] = {start}
    all_nodes = set(cfg.keys())
    rem_nodes = all_nodes - {start}
    for n in rem_nodes:
        dominator[n] = all_nodes

    c = True
    while c:
        c = False
        for n in rem_nodes:
            pred_n = cfg[n][key]
            doms = [dominator[p] for p in pred_n]
            i = set.intersection(*doms) if doms else set()
            v = {n} | i
            if dominator[n] != v:
                c = True
            dominator[n] = v
    return dominator

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
    return (g, cfg.founder.ast_node.lineno, cfg.last_node.ast_node.lineno)

if __name__ == '__main__':
    import json
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('pythonfile', help='The python file to be analyzed')
    parser.add_argument('-d','--dots', action='store_true', help='generate a dot file')
    parser.add_argument('-c','--cfg', action='store_true', help='print cfg')
    parser.add_argument('-x','--coverage', action='store', dest='coverage', type=str, help='coverage file')
    parser.add_argument('-y','--ccoverage', action='store', dest='ccoverage', type=str, help='custom coverage file')
    args = parser.parse_args()
    if args.dots:
        arcs = None
        if args.coverage:
            cdata = coverage.CoverageData()
            cdata.read_file(filename=args.coverage)
            arcs = [(abs(i),abs(j)) for i,j in cdata.arcs(cdata.measured_files()[0])]
        elif args.ccoverage:
            arcs = [(i,j) for i,j in json.loads(open(args.ccoverage).read())]
        cfg = PyCFG()
        cfg.gen_cfg(slurp(args.pythonfile).strip())
        print(CFGNode.to_dot(arcs))
    elif args.cfg:
        cfg = get_cfg(args.pythonfile)
        for i in sorted(cfg):
            print(i,'parents:', cfg[i]['parents'], 'children:', cfg[i]['children'])
