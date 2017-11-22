#!/usr/bin/env python3
#cov.set_option("run:branch", True)

import coverage
import sys
import json
import example
import pycfg
import math

def compute_cost(parent, target, arcs, pdict):
    # The cost of a critical
    return 1

def branch_distance(parent, target, pdict, arcs, seen):
    all_parents = [i for (i,j) in arcs]
    all_targets = [j for (i,j) in arcs]
    # any target, parent is a pair of line numbers.
    # go up the child->parent chain until
    # we get a target branch pair with (condition, next statement).
    # to compute branch distance, we look up if this pair exists in the cdata.arcs.
    # if not, retrieve condition's parents, and for each parent:
    # see if it is a condition. If it is not, get its grand parent
    # resulting in another pair with (condition, stmt) see if it is in cdata.arcs
    # and continue
    seen.add(target)
    parent_dict = pdict[parent]

    gparents = [p for p in parent_dict['parents'] if p not in seen]

    # if we were executed, then there is no cost
    if (parent, target) in arcs: return 0

    # we were not executed. So, where did the flow diverge? Is it here?
    # a divergence happens if parent is executed, but target is not
    if parent in all_parents:
        return compute_cost(parent, target, arcs, pdict)

    # if we can not go further up, we dont know how close we came
    if not gparents: return math.inf

    # so go up the chain.
    pcost = min(branch_distance(gp, parent, pdict, arcs, seen) for gp in gparents)

    is_conditional = len(pdict[target]['children']) > 1
    # the cost of missing a conditional is 1 and that of a non-conditional is 0
    cost = 1 if is_conditional else 0

    return pcost + cost


if __name__ == '__main__':
    cov = coverage.Coverage(branch=True)
    #cov.start()
    #example.gcd(15,12)
    #cov.stop()
    cdata = cov.get_data()
    cdata.read_file('example.coverage')
    f = cdata.measured_files()[0]
    arcs = cdata.arcs(f)
    cfg = dict(pycfg.get_cfg('example.py'))
    target = int(sys.argv[1])
    parents = cfg[target]['parents']
    bd = min(branch_distance(p, target, cfg, arcs, set()) for p in parents)
    print('branch distance(target:%d): %d' % (target, bd))
