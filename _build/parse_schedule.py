"""Turns data/schedule.json (rows pushed daily by the Apps Script) into classes.json and exams.json.
Row cells: [date, day, exam label, exam time, S1..S7]. Dates as YYYY-MM-DD, times as HH:MM. Stdlib only."""
import json, re, sys
SLOTS=[('09:00','10:15'),('10:30','11:45'),('12:00','13:15'),('14:30','15:45'),('16:00','17:15'),('17:30','18:45'),('19:00','20:15')]
CLS=re.compile(r'^(PBM|DMS|MIP|GTM|SSCM|BFA|ISE|CRM|TSB|BMA|Strategic Pricing|CMABN [AB]|E AI S-[AB])[- ]?0*(\d+)$',re.I)
CMAP={'STRATEGIC PRICING':'SP','CMABN A':'CMABN-A','CMABN B':'CMABN-B','E AI S-A':'EAIS-A','E AI S-B':'EAIS-B'}
EX=re.compile(r'^(E\s*AI\s*S|CMABN|BFA|BMA|CRM|DMS|GTM|ISE|MIP|PBM|SP|SSCM|TSB)\b[\s-]*(.*)$',re.I)
def norm_time(t):
    t=str(t or '').strip()
    m=re.match(r'^(\d{1,2}):(\d{2})',t)
    if not m: return ''
    h=int(m.group(1))
    if re.search(r'pm',t,re.I) and h<12: h+=12
    return f'{h:02d}:{m.group(2)}'
def exam_of(label):
    lab=' '.join(str(label).split())
    m=EX.match(lab)
    if not m: return None
    code=re.sub(r'\s','',m.group(1)).upper(); rest=m.group(2)
    if re.search(r'quiz',rest,re.I):
        n=re.search(r'(\d+)',rest); t='Quiz '+str(int(n.group(1))) if n else 'Quiz'
        eid=code.lower()+'-q'+(str(int(n.group(1))) if n else '')
    elif re.search(r'\bET\b|end\s*term',rest,re.I): t='End Term'; eid=code.lower()+'-et'
    elif re.search(r'mid',rest,re.I): t='Mid Term'; eid=code.lower()+'-mt'
    else: return None
    return dict(id=eid,c=code,t=t)
def parse(rows):
    classes=[];exams={}
    for r in rows:
        r=list(r)+['']*(11-len(r))
        m0=re.match(r'^(\d{4}-\d{2}-\d{2})',str(r[0]).strip())
        if not m0: continue
        d=m0.group(1)
        for k,(s,e) in enumerate(SLOTS):
            v=' '.join(str(r[4+k]).split())
            if not v: continue
            m=CLS.match(v)
            if m:
                c=CMAP.get(m.group(1).upper(),m.group(1).upper()); n=int(m.group(2))
                classes.append(dict(id=f"{c.lower()}-{n}-{d}",c=c,n=n,d=d,s=s,e=e,slot=k+1)); continue
            ex=exam_of(v)
            if ex and ex['id'] not in exams: exams[ex['id']]=dict(ex,d=d,s=s,x=0,src='slot')
        lab=str(r[2]).strip()
        if lab:
            ex=exam_of(lab)
            if ex:
                t=norm_time(r[3]); prev=exams.get(ex['id'])
                if t: exams[ex['id']]=dict(ex,d=d,s=t,x=0)
                elif prev and prev['d']==d: pass
                else: exams[ex['id']]=dict(ex,d=d,s='09:00',x=1)
            else: print('unrecognised exam label:',lab,file=sys.stderr)
    ex=sorted(exams.values(),key=lambda e:(e['d'],e['s']))
    for e in ex: e.pop('src',None)
    return classes,ex
if __name__=='__main__':
    src=sys.argv[1] if len(sys.argv)>1 else '../data/schedule.json'
    rows=json.load(open(src))['rows']
    classes,exams=parse(rows)
    json.dump(classes,open('classes.json','w'),separators=(',',':'))
    json.dump(exams,open('exams.json','w'),indent=0)
    print(len(classes),'classes,',len(exams),'exams')
