import json, datetime as dt, sys, os, hashlib, re
from exams import C
OUT=os.environ.get('OUT','site')
EXAMS=json.load(open('exams.json'))
raw=json.load(open('students.json'))
students={r:sorted({c.split('-')[0] for c in v['c']}) for r,v in raw.items()}
sections={r:sorted(v['c']) for r,v in raw.items()}
links=json.load(open('links.json'))
CLASSES=json.load(open('classes.json'))
RESULTS=open('results_locked.json').read()
names={r:' '.join(v['n'].split()) for r,v in raw.items()}
IST=dt.timezone(dt.timedelta(hours=5,minutes=30))
def utc(d,s,add=0):
    t=dt.datetime.fromisoformat(f"{d}T{s}:00").replace(tzinfo=IST)+dt.timedelta(minutes=add)
    return t.astimezone(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def esc(s): return s.replace('\\','\\\\').replace(',','\\,').replace(';','\\;').replace('\n','\\n')
# Version bumps only when the schedule data changes, so unchanged runs produce identical files
_h=hashlib.sha256((json.dumps(EXAMS,sort_keys=True)+json.dumps(CLASSES,sort_keys=True)).encode()).hexdigest()
try: _v=json.load(open('version.json'))
except Exception: _v={'hash':'','version':1,'stamp':dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}
if _v['hash']!=_h:
    if _v['hash']: _v['version']+=1
    _v['hash']=_h; _v['stamp']=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    json.dump(_v,open('version.json','w'),indent=1)
SCHEDULE_VERSION=_v['version']; stamp=_v['stamp']
def ics(exams,name,key):
    L=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//IIMXamday//Term V Exams//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH',
       'X-WR-CALNAME:'+esc(name),'X-WR-TIMEZONE:Asia/Kolkata','REFRESH-INTERVAL;VALUE=DURATION:PT6H','X-PUBLISHED-TTL:PT6H']
    for e in exams:
        cn,fac=C[e['c']]
        desc=f"{cn} ({e['c']}) {e['t']}\n{fac}\nTerm V, EMP MMS Batch 02, IIM Indore. Dates are tentative."
        if e['x']: desc+="\nStart time taken from the session slot, not stated in the schedule."
        L+=['BEGIN:VEVENT',f"UID:{e['id']}-{key}@term5-exams.iimidr",f'DTSTAMP:{stamp}',f'SEQUENCE:{SCHEDULE_VERSION}',
            f"DTSTART:{utc(e['d'],e['s'])}",f"DTEND:{utc(e['d'],e['s'],75)}",
            'SUMMARY:'+esc(f"{e['c']} {e['t']} exam"),'DESCRIPTION:'+esc(desc),'STATUS:CONFIRMED',
            'BEGIN:VALARM','ACTION:DISPLAY','DESCRIPTION:'+esc(f"{e['c']} {e['t']} tomorrow"),'TRIGGER:-P1D','END:VALARM',
            'BEGIN:VALARM','ACTION:DISPLAY','DESCRIPTION:'+esc(f"{e['c']} {e['t']} in 1 hour"),'TRIGGER:-PT1H','END:VALARM',
            'END:VEVENT']
    L.append('END:VCALENDAR')
    out=[]
    for l in L:  # fold at 73 octets
        while len(l.encode())>73:
            out.append(l[:73]); l=' '+l[73:]
        out.append(l)
    return '\r\n'.join(out)+'\r\n'
def class_ics(cls,name,key):
    L=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//IIMXamday//Classes//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH',
       'X-WR-CALNAME:'+esc(name),'X-WR-TIMEZONE:Asia/Kolkata','REFRESH-INTERVAL;VALUE=DURATION:PT6H','X-PUBLISHED-TTL:PT6H']
    for k in cls:
        code,_,sec=k['c'].partition('-');cn,fac=C[code]
        title=f"{code}{' '+sec if sec else ''} class {k['n']}"
        desc=f"{cn}{' (Section '+sec+')' if sec else ''}, session {k['n']}\n{fac}\nTerm V online class, EMP MMS Batch 02, IIM Indore."
        L+=['BEGIN:VEVENT',f"UID:{k['id']}-{key}@iimxamday",f'DTSTAMP:{stamp}',f'SEQUENCE:{SCHEDULE_VERSION}',
            f"DTSTART:{utc(k['d'],k['s'])}",'DTEND:'+utc(k['d'],k['e']),'SUMMARY:'+esc(title),'DESCRIPTION:'+esc(desc),
            'BEGIN:VALARM','ACTION:DISPLAY','DESCRIPTION:'+esc(title+' in 10 minutes'),'TRIGGER:-PT10M','END:VALARM','END:VEVENT']
    L.append('END:VCALENDAR')
    out=[]
    for l in L:
        while len(l.encode())>73: out.append(l[:73]); l=' '+l[73:]
        out.append(l)
    return '\r\n'.join(out)+'\r\n'
def mine(r): return [e for e in EXAMS if e['c'] in students[r]]
if __name__=='__main__':
    feedbase=sys.argv[1] if len(sys.argv)>1 else ''
    for r in students:
        open(f'{OUT}/feeds/{r}.ics','w',newline='').write(ics(mine(r),'IIMXamday '+r,r))
    for r in students:
        mc=[k for k in CLASSES if k['c'] in sections[r]]
        open(f'{OUT}/feeds/{r}-classes.ics','w',newline='').write(class_ics(mc,'IIMXamday classes '+r,r))
    open(OUT+'/feeds/all-exams.ics','w',newline='').write(ics(EXAMS,'IIMXamday (all courses)','all'))
    html=open('template.html').read()
    html=(html.replace('__STUDENTS__',json.dumps(students,separators=(',',':')))
              .replace('__RESULTS__',RESULTS)
              .replace('__CLASSES__',json.dumps(CLASSES,separators=(',',':')))
              .replace('__SECTIONS__',json.dumps(sections,separators=(',',':')))
              .replace('__LINKS__',json.dumps(links,separators=(',',':')))
              .replace('__NAMES__',json.dumps(names,separators=(',',':'),ensure_ascii=False))
              .replace('__EXAMS__',json.dumps(EXAMS,separators=(',',':')))
              .replace('__COURSES__',json.dumps(C,separators=(',',':')))
              .replace('__VERSION__',str(SCHEDULE_VERSION))
              .replace('__SYNCED__',dt.datetime.strptime(stamp,'%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc).astimezone(IST).strftime('%d %b %Y, %I:%M %p IST'))
              .replace('__FEED_BASE__',feedbase))
    open(OUT+'/index.html','w').write(html)
    sw=open(OUT+'/sw.js').read()
    open(OUT+'/sw.js','w').write(re.sub(r'iimxamday-v\d+',f'iimxamday-v{SCHEDULE_VERSION}',sw))
    print(len(students),'feeds; html',len(html))
