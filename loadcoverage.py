#!/usr/bin/env python3
#cov.set_option("run:branch", True)

import coverage
import json
import example
import pycfg

cov = coverage.Coverage(branch=True)
cov.start()
example.gcd(12,15)
cov.stop()
cdata = cov.get_data()

f = cdata.measured_files()[0]
print('Branch arcs')
print(cdata.arcs(f))
parents = dict(pycfg.get_parent_graph('example.py'))
children = dict(pycfg.get_child_graph('example.py'))
print(' '*20)
print('line [parents] (condition, [children])')
print('_'*20)
for k,v in parents.items():
    print(k, v, ('condition:', children[k]) if len(children[k]) > 1 else '_')

# any target is a single line number. go up the child->parent chain until
# we get a target branch pair with (condition, next statement).
# to compute branch distance, we look up if this pair exists in the cdata.arcs.
# if not, retrieve condition's parents, and for each parent:
# see if it is a condition. If it is not, get its grand parent
# resulting in another pair with (condition, stmt) see if it is in cdata.arcs
# and continue

