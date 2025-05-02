from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import random
import lorem
import argparse
import os
from dotenv import load_dotenv

# Build the path to the .env file located in the project root folder
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Retrieve the environment variables with fallback default values if not defined in .env
MONGODB_URI = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("DATABASE_NAME", "cms")

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

# Collections
messages_collection = db['messages']
conversations_collection = db['conversations']
users_collection = db['users']

def clean_existing_messages():
    """Remove all existing messages and conversations"""
    # Get counts before deletion
    message_count = messages_collection.count_documents({})
    conversation_count = conversations_collection.count_documents({})
    
    # Delete all messages and conversations
    messages_result = messages_collection.delete_many({})
    conversations_result = conversations_collection.delete_many({})
    
    print(f"Deleted {messages_result.deleted_count} of {message_count} messages")
    print(f"Deleted {conversation_count} conversations")

def generate_test_messages(clean_first=False):
    # Clean existing messages if requested
    if clean_first:
        clean_existing_messages()
    
    # Get all users from the database
    users = list(users_collection.find())
    
    if not users:
        print("No users found in the database.")
        return
    
    print(f"Found {len(users)} users")
    
    # Create conversations between random pairs of users
    num_conversations = min(10, len(users) * (len(users) - 1) // 2)  # Limit to 10 conversations or all possible pairs
    user_pairs = []
    
    # Generate unique user pairs
    while len(user_pairs) < num_conversations:
        user1 = random.choice(users)
        user2 = random.choice(users)
        if user1['_id'] != user2['_id']:
            pair = sorted([str(user1['_id']), str(user2['_id'])])
            if pair not in user_pairs:
                user_pairs.append(pair)
    
    # Create messages for each conversation
    for participants in user_pairs:
        # Generate 3-8 random messages per conversation
        num_messages = random.randint(3, 8)
        messages = []
        
        for i in range(num_messages):
            # Alternate between users
            sender_idx = i % 2
            receiver_idx = 1 - sender_idx
            
            # Create a message
            message = {
                "_id": ObjectId(),
                "sender_id": participants[sender_idx],
                "receiver_id": participants[receiver_idx],
                "content": lorem.sentence(),
                "created_at": datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24)),
                "is_read": random.choice([True, False])
            }
            
            if message["is_read"]:
                message["read_at"] = message["created_at"] + timedelta(minutes=random.randint(1, 60))
            
            # Insert the message
            messages_collection.insert_one(message)
            messages.append(message)
            
            print(f"Added message from {participants[sender_idx]} to {participants[receiver_idx]}")
        
        # Create conversation with properly formatted last message
        last_message = messages[-1]
        formatted_last_message = {
            "id": str(last_message["_id"]),
            "sender_id": last_message["sender_id"],
            "receiver_id": last_message["receiver_id"],
            "content": last_message["content"],
            "created_at": last_message["created_at"],
            "is_read": last_message["is_read"]
        }
        if "read_at" in last_message:
            formatted_last_message["read_at"] = last_message["read_at"]
        
        conversation = {
            "participants": participants,
            "last_message": formatted_last_message,
            "unread_count": sum(1 for m in messages if not m["is_read"]),
            "updated_at": messages[-1]["created_at"]
        }
        
        # Insert the conversation
        conversations_collection.insert_one(conversation)
        print(f"Created conversation between {participants[0]} and {participants[1]}")

def verify_message_links():
    """Verify that all messages have valid sender and receiver IDs"""
    # Check all messages have valid user references
    invalid_messages = 0
    for message in messages_collection.find():
        sender = users_collection.find_one({"_id": ObjectId(message["sender_id"])})
        receiver = users_collection.find_one({"_id": ObjectId(message["receiver_id"])})
        
        if not sender or not receiver:
            invalid_messages += 1
            print(f"Invalid user reference in message {message['_id']}")
    
    if invalid_messages == 0:
        print("All message user references are valid")
    else:
        print(f"WARNING: {invalid_messages} messages have invalid user references")
    
    # Check all conversations have valid participants
    invalid_conversations = 0
    for conversation in conversations_collection.find():
        for participant_id in conversation["participants"]:
            user = users_collection.find_one({"_id": ObjectId(participant_id)})
            if not user:
                invalid_conversations += 1
                print(f"Invalid participant in conversation {conversation['_id']}")
                break
    
    if invalid_conversations == 0:
        print("All conversation participants are valid")
    else:
        print(f"WARNING: {invalid_conversations} conversations have invalid participants")

if __name__ == "__main__":
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Generate test messages for MongoDB')
    parser.add_argument('--clean', action='store_true', 
                        help='Remove all existing messages before generating new ones')
    args = parser.parse_args()
    
    print(f"Connected to MongoDB at {MONGODB_URI}, using database {MONGODB_DB}")
    print("Starting message generation process...")
    if args.clean:
        print("Clean mode activated - removing existing messages before generation")
    
    generate_test_messages(clean_first=args.clean)
    print("Verifying message links...")
    verify_message_links()
    print("Message generation complete!") 