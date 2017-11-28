#!/usr/bin/env python3

import pycfg
import math
import dexpr
import branchcov
from importlib.machinery import SourceFileLoader

class Fitness:
    def __init__(self, filename, method, path):
        my_module = SourceFileLoader('', filename).load_module()
        fn = getattr(my_module, method)

        self.cdata_arcs, self.source_code, self.branch_cov = branchcov.capture_coverage(fn)

        cfg, founder, last_node = pycfg.get_cfg(filename)
        self.cfg = dict(cfg)
        self.dom = pycfg.compute_dominator(self.cfg, start=founder, key='parents')
        self.postdom = pycfg.compute_dominator(self.cfg, start=last_node, key='children')

        self.path = path

    def print_dom(dom):
        for k in dom: print(k, dom[k])

    def approach_level(self):
        return self._approach_level(reversed(self.path))

    def target(self):
        return self.path[-1]

    def branch_distance(self):
        parents = self.cfg[self.target()]['parents']
        return min(self._branch_distance(p, self.target(), set()) for p in parents)

    def compute_predicate_cost(self, parent, target):
        f,src,l = self.source_code[parent]
        ei = dexpr.DistInterpreter(l)
        v = ei.eval(src)
        return v

    def _branch_distance(self, parent, target, seen):
        seen.add(target)
        parent_dict = self.cfg[parent]

        gparents = [p for p in parent_dict['parents'] if p not in seen]

        # was the parent executed?
        if parent in self.branch_cov:
            # the parent was executed. Hence, if the target is executed
            # then there is no cost.
            if target in self.branch_cov[parent]:
                return 0

            # the target was not executed. Hence the flow diverged here.
            # print(parent, target)
            return self.compute_predicate_cost(parent, target)

        else: # The parent was not executed. So go up the chain

            # if we can not go further up, we dont know how close we came
            if not gparents: return math.inf

            # go up the minimum chain.
            return min(self._branch_distance(gp, parent, seen) for gp in gparents)

    def a_control_dependent_on_b(self, a, b):
        # A has at least 2 successors in CFG
        if len(self.cfg[b]['children']) < 2: return False

        b_successors = self.cfg[b]['children']
        # B dominates A
        v1 = b in self.dom[a]
        # B is not post dominated by A
        v2 = a not in self.postdom[b]
        # there exist a successor for B that is post dominated by A
        v3 = any(a in self.postdom[s] for s in b_successors)
        return v1 and v2 and v3

    def _approach_level(self, path):
        if not path: return 0
        hd, *tl = path
        if not tl: return 0
        cost = 1 if self.a_control_dependent_on_b(hd, tl[0]) else 0
        return cost + self._approach_level(tl)

if __name__ == '__main__':
    import sys
    import example
    path = [int(i) for i in sys.argv[3:]]
    ffn = Fitness(sys.argv[1], sys.argv[2], path)
    print('Approach Level %d' % ffn.approach_level())
    print('Branch distance(target:%d): %d' % (ffn.target(), ffn.branch_distance()))
