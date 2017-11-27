import sys
import json
import inspect

def traceit(frame, event, arg):
    traceit.prevline = vars(traceit).setdefault('prevline', 0)
    traceit.cdata_arcs = vars(traceit).setdefault('cdata_arcs', [])
    if event in ['call', 'return', 'line']: # 'exception'
        line = frame.f_lineno
        source = frame.f_code.co_filename
        myglobals = dict(frame.f_globals) # should we do deep?
        mylocals = frame.f_locals
        myglobals.update(mylocals)
        f = inspect.getframeinfo(frame)
        src = f.code_context[f.index].strip()
        ssrc = None
        myast = None
        if src.startswith('if ') and src.endswith(':'):
            ssrc = src[3:-1].strip()
        elif src.startswith('while ') and src.endswith(':'):
            ssrc = src[5:-1].strip()
        traceit.cdata_arcs.append((source, traceit.prevline, line, ssrc, myglobals))
        traceit.prevline = line
    else: pass
    return traceit

def capture_coverage(fn):
    oldtrace = sys.gettrace()
    sys.settrace(traceit)
    fn()
    sys.settrace(oldtrace)
    branch_cov = {}
    source_code = {}

    for f,i,j,ssrc,l in traceit.cdata_arcs:
        branch_cov.setdefault(i, []).append(j)
        source_code[j] = (f, ssrc, l)

    return (traceit.cdata_arcs, source_code, branch_cov)

if __name__ == '__main__':
    from importlib.machinery import SourceFileLoader
    v = SourceFileLoader('', sys.argv[1]).load_module()
    method = 'main'
    if len(sys.argv) > 2:
        method = sys.argv[2]
    arcs, source, bcov = capture_coverage(getattr(v, method))
    cov = []
    for f,i,j,src,l in arcs:
        cov.append((i,j))
    print(json.dumps(cov))
