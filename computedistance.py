#!/usr/bin/env python3
#cov.set_option("run:branch", True)

import coverage
import inspect
import sys
import json
import example
import pycfg
import math
import ast
import dexpr

global prevline
prevline = 0
global cdata_arcs
cdata_arcs = []
global branch_cov
branch_cov = {}
global source_code
source_code = {}

def traceit(frame, event, arg):
    global prevline
    if event in ['call', 'return', 'line']: # 'exception'
        line = frame.f_lineno
        mylocals = frame.f_locals
        f = inspect.getframeinfo(frame)
        src = f.code_context[f.index].strip()
        ssrc = None
        myast = None
        if src.startswith('if ') and src.endswith(':'):
            ssrc = src[3:-1].strip()
        elif src.startswith('while ') and src.endswith(':'):
            ssrc = src[5:-1].strip()
        cdata_arcs.append((prevline, line, ssrc, mylocals))
        prevline = line
    else: pass
    return traceit


def compute_predicate_cost(parent, target, cfg):
    global branch_cov
    global source_code
    src, l = source_code[parent]
    ei = dexpr.DistInterpreter(l)
    v = ei.eval(src)
    return v

def branch_distance(parent, target, cfg, seen):
    global branch_cov
    seen.add(target)
    parent_dict = cfg[parent]

    gparents = [p for p in parent_dict['parents'] if p not in seen]

    # was the parent executed?
    if parent in branch_cov:
        # the parent was executed. Hence, if the target is executed
        # then there is no cost.
        if target in branch_cov[parent]:
            return 0

        # the target was not executed. Hence the flow diverged here.
        return compute_predicate_cost(parent, target, cfg)

    else: # The parent was not executed. So go up the chain

        # if we can not go further up, we dont know how close we came
        if not gparents: return math.inf

        # go up the minimum chain.
        path_cost = min(branch_distance(gp, parent, cfg, seen) for gp in gparents)

        is_conditional = len(cfg[target]['children']) > 1
        # the cost of missing a conditional is 1 and that of a non-conditional is 0
        node_cost = 1 if is_conditional else 0

        return path_cost + node_cost

def compute_dominator(dominator, cfg, start = 0, key='parents'):
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

def a_control_dependent_on_b(a, b, cfg, dom, postdom):
    # A has at least 2 successors in CFG
    if len(cfg[b]['children']) < 2: return False

    b_successors = cfg[b]['children']
    # B dominates A
    v1 = b in dom[a]
    # B is not post dominated by A
    v2 = a not in postdom[b]
    # there exist a successor for B that is post dominated by A
    v3 = any(a in postdom[s] for s in b_successors)
    return v1 and v2 and v3

def approach_level(path, cfg, dom, postdom):
    if not path: return 0
    hd, *tl = path
    if not tl: return 0
    cost = 1 if a_control_dependent_on_b(hd, tl[0], cfg, dom, postdom) else 0
    return cost + approach_level(tl, cfg, dom, postdom)

if __name__ == '__main__':
    cov = coverage.Coverage(branch=True)

    trace = sys.gettrace()
    sys.settrace(traceit)
    example.gcd(15,12)
    sys.settrace(trace)

    for i,j,src,l in cdata_arcs:
        branch_cov.setdefault(i, []).append(j)
        source_code[j] = (src, l)

    cfg, founder, last_node = pycfg.get_cfg('example.py')
    cfg = dict(cfg)
    #print(v)
    dom = {}
    print('dominators')
    compute_dominator(dom, cfg, start=founder, key='parents')
    for k in dom:
        print(k, dom[k])

    pdom = {}
    print('postdominators')
    compute_dominator(pdom, cfg, start=last_node, key='children')
    for k in pdom:
        print(k, pdom[k])

    target = int(sys.argv[1])
    parents = cfg[target]['parents']
    bd = min(branch_distance(p, target, cfg, set()) for p in parents)
    print('branch distance(target:%d): %d' % (target, bd))

    path = [int(i) for i in sys.argv[2:]]
    al = approach_level(reversed(path), cfg, dom, pdom)
    print('approach level(%s): %d' % (path, al))
