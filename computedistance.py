#!/usr/bin/env python3
#cov.set_option("run:branch", True)

import coverage
import sys
import json
import example
import pycfg
import math

def compute_predicate_cost(parent, target, branch_cov, cfg):
    # The cost of a critical
    return 1

def branch_distance(parent, target, cfg, branch_cov, seen):
    seen.add(target)
    parent_dict = cfg[parent]

    gparents = [p for p in parent_dict['parents'] if p not in seen]

    # was the parent executed?
    if parent in branch_cov:
        # the parent was executed. Hence, if the target is executed
        # then there is no cost.
        if target in branch_cov[parent]: return 0

        # the target was not executed. Hence the flow diverged here.
        return compute_predicate_cost(parent, target, branch_cov, cfg)

    else: # The parent was not executed. So go up the chain

        # if we can not go further up, we dont know how close we came
        if not gparents: return math.inf

        # go up the minimum chain.
        path_cost = min(branch_distance(gp, parent, cfg, branch_cov, seen) for gp in gparents)

        is_conditional = len(cfg[target]['children']) > 1
        # the cost of missing a conditional is 1 and that of a non-conditional is 0
        node_cost = 1 if is_conditional else 0

        return path_cost + node_cost


if __name__ == '__main__':
    cov = coverage.Coverage(branch=True)
    #cov.start()
    #example.gcd(15,12)
    #cov.stop()
    cdata = cov.get_data()
    cdata.read_file('example.coverage')
    cdata_arcs = cdata.arcs(cdata.measured_files()[0])
    branch_cov = {}

    for i,j in cdata_arcs:
        branch_cov.setdefault(i, []).append(j)

    cfg = dict(pycfg.get_cfg('example.py'))
    target = int(sys.argv[1])
    parents = cfg[target]['parents']
    bd = min(branch_distance(p, target, cfg, branch_cov, set()) for p in parents)
    print('branch distance(target:%d): %d' % (target, bd))
