"""Encrypt the batch directory with the passphrase shared in the batch group.

  python3 encrypt_directory.py directory_plain.json "batch passphrase"

Writes directory_enc.json, which is the only version that goes into the repo.
The plain file and the passphrase stay off GitHub.
"""
import json, sys, os, base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITER = 200000
if len(sys.argv) < 3: sys.exit(__doc__)
people = json.load(open(sys.argv[1]))
passphrase = sys.argv[2].strip().lower()
salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(passphrase.encode())
ct = AESGCM(key).encrypt(iv, json.dumps(people, ensure_ascii=False, separators=(',', ':')).encode(), None)
b64 = lambda b: base64.b64encode(b).decode()
json.dump({'iter': ITER, 'count': len(people), 'blob': [b64(salt), b64(iv), b64(ct)]},
          open('directory_enc.json', 'w'), separators=(',', ':'))
print(f'{len(people)} profiles encrypted into directory_enc.json')
