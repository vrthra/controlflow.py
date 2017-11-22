#!/usr/bin/env python3
#cov.set_option("run:branch", True)

import coverage
import sys
import json
import example
import pycfg

def branch_distance(target, pdict, arcs, seen):
    arc_first = [i for (i,j) in arcs]
    arc_second = [j for (i,j) in arcs]
    # any target is a single line number. go up the child->parent chain until
    # we get a target branch pair with (condition, next statement).
    # to compute branch distance, we look up if this pair exists in the cdata.arcs.
    # if not, retrieve condition's parents, and for each parent:
    # see if it is a condition. If it is not, get its grand parent
    # resulting in another pair with (condition, stmt) see if it is in cdata.arcs
    # and continue
    seen.add(target)
    if target not in pdict: return 0
    (parents, children), cost = pdict[target]
    if target in arc_second: return cost

    return min(branch_distance(p, pdict, arcs, seen) for p in parents if p not in seen) + cost


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
    pdict = {}
    for k,v in cfg.items():
        parents,children = v
        if len(children) > 1:
            pdict[k] = (v, 1)
        else:
            pdict[k] = (v, 0)
    print('branch distance:',branch_distance(int(sys.argv[1]), pdict, arcs, set()))
