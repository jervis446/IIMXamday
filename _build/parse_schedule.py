"""Turns data/schedule.json (rows pushed daily by the Apps Script) into classes.json and exams.json.
Row cells: [date, day, exam label, exam time, S1..S8]. Dates as YYYY-MM-DD or 21-Nov-26, times as HH:MM. Stdlib only."""
import json, re, sys, datetime as dt
SLOTS=[('09:00','10:15'),('10:30','11:45'),('12:00','13:15'),('14:30','15:45'),('16:00','17:15'),('17:30','18:45'),('19:00','20:15'),('20:00','21:15')]
# Term VI cell labels: "SPFDF A 1", "AFBD-1", "CCM01", "CMOD B3", "Simulation Sec A-1", "MMM" (Man and Machine, unnumbered)
CLS=re.compile(r'^(SPFDF|CMOD|AFBD|AOMDM|CCM|CBAI|EOI|SCAC|BM|PSF|OC|FSA|MM|Simulation)(?:\s+Sec)?[\s-]*([AB])?[\s-]*0*(\d+)$',re.I)
UNNUMBERED={'MMM':'MM'}
SECTIONED={'SPFDF','CMOD','SIM'}
EX=re.compile(r'^(SPFDF|CMOD|AFBD|AOMDM|CCM|CBAI|EOI|SCAC|BM|PSF|OC|FSA|MM|M&M)\b[\s-]*(.*)$',re.I)
EVENTS={'industry expert sessions':('Industry Expert Sessions',2),'batch meet':('Batch Meet @ Mumbai',4)}
def norm_date(v):
    v=str(v or '').strip()
    m=re.match(r'^(\d{4}-\d{2}-\d{2})',v)
    if m: return m.group(1)
    try: return dt.datetime.strptime(v,'%d-%b-%y').strftime('%Y-%m-%d')
    except ValueError: return ''
def norm_time(t):
    t=' '.join(str(t or '').split())
    m=re.match(r'^(\d{1,2}):(\d{2})(?::\d{2})?\s*([ap]\.?m\.?)?', t, re.I)
    if not m: return ''
    h=int(m.group(1)); ap=(m.group(3) or '').lower()
    if ap.startswith('p') and h<12: h+=12
    if ap.startswith('a') and h==12: h=0
    return f'{h:02d}:{m.group(2)}'
def exam_of(label):
    lab=' '.join(str(label).split())
    m=EX.match(lab)
    if not m: return None
    code=re.sub(r'\s','',m.group(1)).upper().replace('M&M','MM'); rest=m.group(2)
    if re.search(r'quiz',rest,re.I):
        n=re.search(r'(\d+)',rest); t='Quiz '+str(int(n.group(1))) if n else 'Quiz'
        eid=code.lower()+'-q'+(str(int(n.group(1))) if n else '')
    elif re.search(r'\bET\b|end\s*term',rest,re.I): t='End Term'; eid=code.lower()+'-et'
    elif re.search(r'assignment|submission',rest,re.I): t='Assignment'; eid=code.lower()+'-as'
    elif re.search(r'present|viva',rest,re.I): t='Presentation'; eid=code.lower()+'-pr'
    elif re.search(r'mid',rest,re.I): t='Mid Term'; eid=code.lower()+'-mt'
    else: return None
    return dict(id=eid,c=code,t=t)
def parse(rows):
    classes=[];exams={};events=[];seq={}
    for r in rows:
        r=list(r)+['']*(12-len(r))
        d=norm_date(r[0])
        if not d: continue
        for k,(st,en) in enumerate(SLOTS):
            v=' '.join(str(r[4+k]).split())
            if not v: continue
            ev=next((e for key,e in EVENTS.items() if v.lower().startswith(key)),None)
            if ev:
                if not any(x['d']==d and x['t']==ev[0] for x in events):
                    end=SLOTS[min(k+ev[1]-1,len(SLOTS)-1)][1]
                    events.append(dict(id=re.sub(r'\W+','-',ev[0].lower())+'-'+d,d=d,s=st,e=end,t=ev[0]))
                continue
            if v.upper() in UNNUMBERED:
                c=UNNUMBERED[v.upper()]; seq[c]=seq.get(c,0)+1
                classes.append(dict(id=f"{c.lower()}-{seq[c]}-{d}-{k+1}",c=c,n=seq[c],d=d,s=st,e=en,slot=k+1)); continue
            m=CLS.match(v)
            if m:
                c=m.group(1).upper()
                if c=='SIMULATION': c='SIM'
                if m.group(2) and c in SECTIONED: c+='-'+m.group(2).upper()
                n=int(m.group(3))
                classes.append(dict(id=f"{c.lower()}-{n}-{d}",c=c,n=n,d=d,s=st,e=en,slot=k+1)); continue
            ex=exam_of(v)
            if ex and ex['id'] not in exams: exams[ex['id']]=dict(ex,d=d,s=st,x=0,src='slot')
        labels=[x.strip() for x in str(r[2]).replace('\r','').split('\n') if x.strip()]
        times=[x.strip() for x in str(r[3]).replace('\r','').split('\n') if x.strip()]
        for k,lab in enumerate(labels):
            ex=exam_of(lab)
            if not ex:
                print('unrecognised exam label:',lab,file=sys.stderr); continue
            t=norm_time(times[k]) if k<len(times) else (norm_time(times[0]) if len(times)==1 and len(labels)==1 else '')
            prev=exams.get(ex['id'])
            if t: exams[ex['id']]=dict(ex,d=d,s=t,x=0)
            elif prev and prev['d']==d: pass
            else: exams[ex['id']]=dict(ex,d=d,s='09:00',x=1)
    try:
        for o in json.load(open('exam_overrides.json')):
            if o['id'] not in exams: exams[o['id']]=o
    except FileNotFoundError: pass
    ex=sorted(exams.values(),key=lambda e:(e['d'],e['s']))
    for e in ex: e.pop('src',None)
    return classes,ex,events
if __name__=='__main__':
    src=sys.argv[1] if len(sys.argv)>1 else '../data/schedule.json'
    rows=json.load(open(src))['rows']
    classes,exams,events=parse(rows)
    try:
        camp=json.load(open('campus.json'))
    except FileNotFoundError:
        camp={'classes':[],'events':[]}
    have={(k['c'],k['n'],k['d']) for k in classes}
    for k in camp['classes']:
        if (k['c'],k['n'],k['d']) in have: continue
        k=dict(k); k['id']=f"{k['c'].lower()}-{k['n']}-{k['d']}"; k['campus']=1
        classes.append(k)
    classes.sort(key=lambda k:(k['d'],k['s'],k['c']))
    json.dump(classes,open('classes.json','w'),separators=(',',':'))
    json.dump(exams,open('exams.json','w'),indent=0)
    camp['events']=events
    json.dump(camp,open('campus.json','w'),indent=1,ensure_ascii=False)
    print(len(classes),'classes,',len(exams),'exams')
