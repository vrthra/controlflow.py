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
        if target in branch_cov[parent]: return 0

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

if __name__ == '__main__':
    cov = coverage.Coverage(branch=True)

    trace = sys.gettrace()
    sys.settrace(traceit)
    example.gcd(15,12)
    sys.settrace(trace)

    for i,j,src,l in cdata_arcs:
        branch_cov.setdefault(i, []).append(j)
        source_code[j] = (src, l)

    cfg = dict(pycfg.get_cfg('example.py'))
    target = int(sys.argv[1])
    parents = cfg[target]['parents']
    bd = min(branch_distance(p, target, cfg, set()) for p in parents)
    print('branch distance(target:%d): %d' % (target, bd))
