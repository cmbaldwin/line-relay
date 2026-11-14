import sys
from ApplicationServices import *
from AppKit import NSWorkspace
def g(e,a):
    err,v=AXUIElementCopyAttributeValue(e,a,None); return v if err==0 else None
def dump(e,d,maxd):
    r=g(e,'AXRole'); extra=[f"{k}={str(g(e,k))[:60]!r}" for k in ('AXTitle','AXDescription','AXValue','AXIdentifier','AXSubrole') if g(e,k)]
    print('  '*d+str(r),*extra)
    if d<maxd:
        for c in g(e,'AXChildren') or []: dump(c,d+1,maxd)
app=[a for a in NSWorkspace.sharedWorkspace().runningApplications() if a.localizedName()=='LINE'][0]
ax=AXUIElementCreateApplication(app.processIdentifier())
print('windows:',len(g(ax,'AXWindows') or []), 'focused:',g(ax,'AXFocusedWindow') is not None)
for w in g(ax,'AXChildren') or []: dump(w,0,int(sys.argv[1]) if len(sys.argv)>1 else 6)
