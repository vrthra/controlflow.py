#!/usr/bin/env python3

import coverage
import json

cov = coverage.CoverageData()
cov.read_file('.coverage')
f = cov.measured_files()[0]
print(cov.arcs(f))
parents = []
with open('parents.json') as f:
    for line in f:
        parents.append(json.loads(line))
parents = dict(parents)
children = []
with open('children.json') as f:
    for line in f:
        children.append(json.loads(line))
children = dict(children)

for k,v in parents.items():
    print(k, v, ('condition:', children[k]) if len(children[k]) > 1 else '_')

# any target is a single line number. go up the child->parent chain until
# we get a target branch pair with (condition, next statement).
# to compute branch distance, we look up if this pair exists in the cov.arcs.
# if not, retrieve condition's parents, and for each parent:
# see if it is a condition. If it is not, get its grand parent
# resulting in another pair with (condition, stmt) see if it is in cov.arcs
# and continue

