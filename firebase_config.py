import firebase_admin
from firebase_admin import credentials, db
import os

try:
    # IMPORTANT: Create a `firebase-creds.json` file in your project root.
    cred = credentials.Certificate('firebase-creds.json')
    # IMPORTANT: Go to your Firebase project -> Realtime Database -> Rules and set them to true for read and write.
    # In production, you'll want more secure rules.
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ.get('FIREBASE_DATABASE_URL') # Set this as an environment variable
    })
    print("Firebase connected successfully!")
except Exception as e:
    print(f"Error connecting to Firebase: {e}")
    print("Please ensure 'firebase-creds.json' is present and you have set the FIREBASE_DATABASE_URL environment variable.")
    db = None

def get_db():
    if db is not None:
        return db.reference('/')
    return None

# Example of how to use it in other files:
# from firebase_config import get_db
# db = get_db()
# if db:
#   db.child('games').set({'example': 'data'}) 