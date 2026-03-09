#!/usr/bin/env python3
"""Check what's in Firebase alerts path"""
import os
import firebase_admin
from firebase_admin import credentials, db
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
firebase_key_path = os.path.join(base_dir, 'firebase-key.json')
cred = credentials.Certificate(firebase_key_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://alarmes-7adaa-default-rtdb.europe-west1.firebasedatabase.app/'
})

ref = db.reference('alerts')
data = ref.get()
print(f"Current data in /alerts: {json.dumps(data, indent=2)}")
