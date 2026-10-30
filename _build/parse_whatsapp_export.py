"""Turn an exported WhatsApp chat into job postings for the app.

In WhatsApp: open the referral group, tap the group name, Export chat, Without media.
Then run:  python3 parse_whatsapp_export.py "WhatsApp Chat with ....txt"
It merges into ../data/jobs.json, keeping anything already there.
Each message that looks like a posting becomes an entry you can edit afterwards.
"""
import sys, re, json, os, hashlib, datetime as dt

LINE = re.compile(r'^\[?(\d{1,2}[/.]\d{1,2}[/.]\d{2,4}),?\s+(\d{1,2}:\d{2})(?::\d{2})?\s*([ap]m)?\]?\s*[-–]?\s*([^:]{1,40}?):\s(.*)$', re.I)
JOBWORDS = re.compile(r'\b(hiring|referral|refer|opening|openings|role|position|vacancy|apply|jd|job|we are looking|looking for)\b', re.I)
SYSTEM = re.compile(r'(created this group|attached:|<attached|document omitted|changed their phone number|added you|joined using|left$|changed the subject|changed this group|omitted|deleted|security code|pinned a message|turned on admin)', re.I)
GREETING = re.compile(r'^(hi|hello|hey|dear|good (morning|evening|afternoon))\b[\s,!:-]*(all|team|everyone|folks|guys)?[\s,!:-]*$', re.I)
FIELD = re.compile(r'^\s*(role|position|designation|job title|title)\s*[:\-]\s*(.+)$', re.I)
COMPANY_FIELD = re.compile(r'^\s*(company|organisation|organization|client)\s*[:\-]\s*(.+)$', re.I)
PHONE = re.compile(r'(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')
DOMAINS = [('Data and AI', r'data scien|machine learning|\bml\b|\bai\b|analytics|data engineer'),
           ('Engineering', r'developer|engineer|sde|backend|frontend|full stack|devops|qa\b|tester'),
           ('Product', r'product manager|product owner|\bpm\b|apm\b'),
           ('Consulting', r'consultant|consulting|strategy'),
           ('Finance', r'finance|accounts|audit|fp&a|investment|credit|treasury'),
           ('Marketing', r'marketing|brand|seo|content|growth'),
           ('Sales', r'sales|business development|\bbde\b|account manager'),
           ('HR', r'\bhr\b|recruit|talent|people ops'),
           ('Operations', r'operations|supply chain|logistics|procurement')]
URL = re.compile(r'https?://\S+')
COMPANY = re.compile(r'\b(?:at|@|company)\s*[:\-]?\s*([A-Z][\w&.\- ]{2,30})')
LOC = re.compile(r'\b(Bangalore|Bengaluru|Mumbai|Pune|Hyderabad|Chennai|Delhi|Gurgaon|Gurugram|Noida|Kolkata|Indore|Remote)\b', re.I)
EXP = re.compile(r'(\d+\s*(?:to|-|\+)?\s*\d*\s*(?:years|yrs|yoe))', re.I)

def parse(path):
    out, cur = [], None
    for raw in open(path, encoding='utf-8', errors='ignore'):
        line = raw.rstrip('\n').replace('\u200e', '')
        m = LINE.match(line)
        if m:
            if cur: out.append(cur)
            d, t, ampm, who, msg = m.groups()
            cur = {'d': d, 't': t, 'ampm': ampm or '', 'who': who.strip(), 'msg': msg}
        elif cur:
            cur['msg'] += '\n' + line
    if cur: out.append(cur)
    return out

def when(e):
    for fmt in ('%d/%m/%Y %H:%M', '%d/%m/%y %H:%M', '%m/%d/%Y %H:%M', '%m/%d/%y %H:%M'):
        try:
            stamp = dt.datetime.strptime(f"{e['d']} {e['t']}", fmt)
            if e['ampm'].lower() == 'pm' and stamp.hour < 12: stamp += dt.timedelta(hours=12)
            if e['ampm'].lower() == 'am' and stamp.hour == 12: stamp -= dt.timedelta(hours=12)
            return stamp.strftime('%Y-%m-%dT%H:%M:00+05:30')
        except ValueError:
            continue
    return ''

def title_of(msg):
    for line in msg.splitlines():
        m = FIELD.match(line)
        if m: return m.group(2).strip(' *_-')[:80]
    for line in msg.splitlines():
        t = line.strip(' *_-\u2022')
        if not t or GREETING.match(t) or t.startswith('http') or len(t) < 12: continue
        if re.search(r'\.(pdf|docx?|jpg|png)\b', t, re.I): continue
        return t[:80]
    return ''

def company_of(msg):
    for line in msg.splitlines():
        m = COMPANY_FIELD.match(line)
        if m: return m.group(2).strip(' *_-')[:40]
    m = COMPANY.search(msg)
    return m.group(1).strip()[:40] if m else ''

def domain_of(msg):
    for name, pat in DOMAINS:
        if re.search(pat, msg, re.I): return name
    return ''

def redact(text):
    text = PHONE.sub('[number removed]', text)
    return EMAIL.sub('[email removed]', text)

def clean_name(who):
    who = who.strip().lstrip('~').strip()
    who = re.sub(r'\s*(IIMI|IIM Indore|EMP|MMS)\s*$', '', who, flags=re.I).strip()
    return '' if who.startswith('+') or re.fullmatch(r'[\d\s+-]+', who) else who

def to_job(e):
    msg = e['msg'].strip()
    if len(msg) < 40 or not JOBWORDS.search(msg) or SYSTEM.search(msg): return None
    first = title_of(msg)
    if not first: return None
    link = URL.search(msg)
    loc = LOC.search(msg)
    exp = EXP.search(msg)
    return {
        'id': 'w' + hashlib.sha1(msg.encode()).hexdigest()[:8],
        'posted': when(e),
        'title': first[:80],
        'company': company_of(msg),
        'loc': loc.group(1).title() if loc else '',
        'type': '', 'exp': exp.group(1) if exp else '', 'domain': domain_of(msg),
        'link': link.group(0).rstrip('.,)') if link else '',
        'notes': redact(msg)[:700],
        'by': clean_name(e['who']),
        'ph': '', 'src': 'WhatsApp',
    }

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    found, seen_text = [], set()
    for e in parse(sys.argv[1]):
        j = to_job(e)
        if not j or not j['posted']: continue
        key = re.sub(r'\W+', '', j['notes'].lower())[:120]
        if key in seen_text: continue
        seen_text.add(key); found.append(j)
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'jobs.json')
    try: existing = json.load(open(path))
    except Exception: existing = []
    seen = {j['id'] for j in existing}
    added = [j for j in found if j['id'] not in seen]
    allj = sorted(existing + added, key=lambda j: j.get('posted', ''), reverse=True)
    json.dump(allj, open(path, 'w'), ensure_ascii=False, indent=1)
    print(f'{len(found)} postings found in the export, {len(added)} new, {len(allj)} total in data/jobs.json')
    print('Edit data/jobs.json to tidy titles or add domains, then commit.')
