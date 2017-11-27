import sys
import json
import inspect

def traceit(frame, event, arg):
    traceit.prevline = vars(traceit).setdefault('prevline', 0)
    traceit.cdata_arcs = vars(traceit).setdefault('cdata_arcs', [])
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
        traceit.cdata_arcs.append((traceit.prevline, line, ssrc, mylocals))
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

    for i,j,src,l in sorted(traceit.cdata_arcs):
        branch_cov.setdefault(i, []).append(j)
        source_code[j] = (src, l)

    return (traceit.cdata_arcs, source_code, branch_cov)

if __name__ == '__main__':
    import example
    arcs, source, bcov = capture_coverage(example.main)
    cov = []
    for i,j,src,l in sorted(arcs):
        cov.append((i,j))
    print(json.dumps(cov))
