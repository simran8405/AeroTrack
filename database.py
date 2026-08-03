from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv(dotenv_path=".env")

# Read MongoDB URI
MONGO_URI = os.getenv("MONGO_URI")

print("MONGO_URI loaded:", MONGO_URI is not None)

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Test connection
client.admin.command("ping")

print("MongoDB Atlas Connected Successfully!")

# Select database
db = client["AeroTrackDB"]

# Collections
baggage_collection = db["baggage"]
lostfound_collection = db["lostfound"]

print("Database Name:", db.name)
print("Collections:", db.list_collection_names())
