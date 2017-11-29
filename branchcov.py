import sys
import inspect
import re

# these control flow contstructs have conditionals we can evaluate
Control_Flow = ['if', 'elif', 'while', 'for']
Control_Flow_Re = [re.compile(r'^ *%s +(.+) *: *' % i) for i in Control_Flow]
# else, continue, break, and pass do not have conditionals
# that can be evaluated.

def traceit(frame, event, arg):
    traceit.prevline = vars(traceit).setdefault('prevline', 0)
    traceit.cov_arcs = vars(traceit).setdefault('cov_arcs', [])

    if event in ['call', 'return', 'line']:
        fname, line = frame.f_code.co_filename, frame.f_lineno
        myvars = {**frame.f_globals, **frame.f_locals} # should we do deep copy?
        finfo = inspect.getframeinfo(frame)
        src = finfo.code_context[finfo.index]
        matches = (ctrl.match(src) for ctrl in Control_Flow_Re)
        conditional = next((m.group(1) for m in matches if m), None)

        traceit.cov_arcs.append((fname, traceit.prevline, line, conditional, myvars))
        traceit.prevline = line
    else: pass # 'exception'
    return traceit

def capture_coverage(fn):
    oldtrace = sys.gettrace()
    sys.settrace(traceit)
    fn()
    sys.settrace(oldtrace)
    branch_cov = {}
    source_code = {}

    for f,i,j,conditional,l in traceit.cov_arcs:
        branch_cov.setdefault(i, set()).add(j)
        source_code[j] = (f, conditional, l)

    return (traceit.cov_arcs, source_code, branch_cov)

if __name__ == '__main__':
    import json
    from importlib.machinery import SourceFileLoader
    v = SourceFileLoader('', sys.argv[1]).load_module()
    method = sys.argv[2] if len(sys.argv) > 2 else 'main'
    arg = sys.argv[3] if len(sys.argv) > 3 else '%20abc'
    arcs, source, bcov = capture_coverage(lambda: getattr(v, method)(arg))
    cov = [ (i,j) for f,i,j,src,l in arcs]
    print(json.dumps(cov), file=sys.stderr)
