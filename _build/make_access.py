"""Build the sign-in keys, the encrypted batch directory and the encrypted results.

  python3 make_access.py directory_plain.json /path/to/phones_private.json [results_plain.json]

Writes directory_enc.json (one copy, encrypted with a random master key) and
access.json (that master key wrapped for each roll number with their own mobile).
Neither file contains a phone number. Keep the inputs off GitHub.
"""
import json, sys, os, base64, hashlib
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITER = 150000
b64 = lambda b: base64.b64encode(b).decode()

def norm(d):
    d = ''.join(c for c in str(d) if c.isdigit())
    if len(d) == 12 and d.startswith('91'): d = d[2:]
    if len(d) == 11 and d.startswith('0'): d = d[1:]
    return d

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    people = json.load(open(sys.argv[1]))
    raw = json.load(open(sys.argv[2]))
    phones = {k: [norm(x) for x in (v if isinstance(v, list) else [v])] for k, v in raw.items()}

    master = os.urandom(32)
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(master).encrypt(iv, json.dumps(people, ensure_ascii=False, separators=(',', ':')).encode(), None)
    json.dump({'count': len(people), 'blob': [b64(iv), b64(ct)]},
              open('directory_enc.json', 'w'), separators=(',', ':'))

    try:
        res = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else json.load(open('results_plain.json'))
        riv = os.urandom(12)
        rct = AESGCM(master).encrypt(riv, json.dumps(res, separators=(',', ':')).encode(), None)
        json.dump({'courses': res['courses'], 'count': len(res['results']), 'blob': [b64(riv), b64(rct)]},
                  open('results_enc.json', 'w'), separators=(',', ':'))
        print(f"{len(res['results'])} result sheets encrypted into results_enc.json")
    except FileNotFoundError:
        print('no results_plain.json, skipping results')

    wraps, total = {}, 0
    for roll, nums in phones.items():
        entries = []
        for phone in dict.fromkeys(n for n in nums if len(n) == 10):
            s, i = os.urandom(16), os.urandom(12)
            key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=s, iterations=ITER).derive((roll + ':' + phone).encode())
            entries.append([b64(s), b64(i), b64(AESGCM(key).encrypt(i, master, None))])
        if entries: wraps[roll] = entries; total += len(entries)
    json.dump({'iter': ITER, 'wraps': wraps}, open('access.json', 'w'), separators=(',', ':'))
    print(f'{len(people)} profiles encrypted, {total} sign-in keys across {len(wraps)} roll numbers')
