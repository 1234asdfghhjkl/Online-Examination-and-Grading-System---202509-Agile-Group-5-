import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables
load_dotenv()

firebase_cert_path = os.getenv("FIREBASE_CERT", "firebase.json")

if not os.path.exists(firebase_cert_path):
    raise RuntimeError(f"Firebase cert file not found at: {firebase_cert_path}")

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_cert_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
