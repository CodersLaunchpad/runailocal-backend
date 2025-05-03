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
MINIO_ENDPOINT = os.getenv("MINIO_SERVER", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_USERNAME", "minioaccesskey")
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "miniosecretkey")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "your-bucket-name")
# Convert the SECURE value to a boolean; accepts "True", "true", "1", etc.
SECURE = os.getenv("SECURE", "False").lower() in ['true', '1', 't']

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

# Collections
articles_collection = db['articles']
comments_collection = db['comments']
users_collection = db['users']
notifications_collection = db['notifications']

def clean_existing_comments():
    """Remove all existing comments and clear comment references from articles"""
    # Get count before deletion
    comment_count = comments_collection.count_documents({})
    
    # Delete all comments
    result = comments_collection.delete_many({})
    
    print(f"Deleted {result.deleted_count} of {comment_count} comments")
    
    # Clear comment arrays in all articles
    articles_update = articles_collection.update_many(
        {},
        {"$set": {"comments": []}}
    )
    
    print(f"Cleared comments array in {articles_update.modified_count} articles")

def generate_test_comments(clean_first=False):
    # Clean existing comments if requested
    if clean_first:
        clean_existing_comments()
    
    # Get all articles and users from the database
    articles = list(articles_collection.find())
    users = list(users_collection.find())
    
    if not articles:
        print("No articles found in the database.")
        return
        
    if not users:
        print("No users found in the database.")
        return
    
    print(f"Found {len(articles)} articles and {len(users)} users")
    
    # Dictionary to keep track of comments per article
    article_comments = {}
    
    # First pass: create base comments for each article
    for article in articles:
        article_id = article['_id']
        article_comments[article_id] = []
        
        # Generate 3-8 random comments per article
        num_comments = random.randint(3, 8)
        
        for _ in range(num_comments):
            # Select a random user
            user = random.choice(users)
            
            # Create a comment
            comment = {
                "_id": ObjectId(),
                "text": lorem.paragraph(),
                "article_id": article_id,
                "parent_comment_id": None,  # Base comment
                "user_id": user['_id'],
                "username": user.get('username', 'unknown'),
                "user_first_name": user.get('first_name', 'Unknown'),
                "user_last_name": user.get('last_name', 'User'),
                "user_type": user.get('user_type', 'normal'),
                "created_at": datetime.now(timezone.utc)
            }
            
            # Insert the comment
            comments_collection.insert_one(comment)
            
            # Store comment ID for potential replies
            article_comments[article_id].append(comment['_id'])
            
            # Add comment to article's comments array
            articles_collection.update_one(
                {"_id": article_id},
                {"$push": {"comments": comment['_id']}}
            )
            
            print(f"Added base comment {comment['_id']} to article {article_id}")
    
    # Second pass: create reply comments (30% chance of reply)
    for article_id, comment_ids in article_comments.items():
        # Skip if there are no comments to reply to
        if not comment_ids:
            continue
            
        # Determine number of replies (0-3 per article)
        num_replies = random.randint(0, min(3, len(comment_ids)))
        
        for _ in range(num_replies):
            # Select a random user and parent comment
            user = random.choice(users)
            parent_comment_id = random.choice(comment_ids)
            
            # Create a reply comment
            reply = {
                "_id": ObjectId(),
                "text": lorem.paragraph(),
                "article_id": article_id,
                "parent_comment_id": parent_comment_id,
                "user_id": user['_id'],
                "username": user.get('username', 'unknown'),
                "user_first_name": user.get('first_name', 'Unknown'),
                "user_last_name": user.get('last_name', 'User'),
                "user_type": user.get('user_type', 'normal'),
                "created_at": datetime.now(timezone.utc)
            }
            
            # Insert the reply
            comments_collection.insert_one(reply)
            
            # Add reply to article's comments array
            articles_collection.update_one(
                {"_id": article_id},
                {"$push": {"comments": reply['_id']}}
            )
            
            print(f"Added reply comment {reply['_id']} to article {article_id} (parent: {parent_comment_id})")

def verify_comment_links():
    """Verify that all articles have at least one comment and all comments have valid references"""
    # Check all articles have comments
    articles_without_comments = articles_collection.count_documents({"comments": {"$size": 0}})
    
    if articles_without_comments > 0:
        print(f"WARNING: {articles_without_comments} articles have no comments")
    else:
        print("All articles have at least one comment")
    
    # Check all parent comment IDs are valid
    all_comment_ids = set(comment['_id'] for comment in comments_collection.find({}, {"_id": 1}))
    
    invalid_parent_refs = 0
    for comment in comments_collection.find({"parent_comment_id": {"$ne": None}}):
        if comment['parent_comment_id'] not in all_comment_ids:
            invalid_parent_refs += 1
            print(f"Invalid parent comment reference: {comment['_id']} -> {comment['parent_comment_id']}")
    
    if invalid_parent_refs == 0:
        print("All parent comment references are valid")
    else:
        print(f"WARNING: {invalid_parent_refs} comments have invalid parent references")

def initialize_notifications_collection():
    """Ensure notifications collection exists with proper indexes"""
    if 'notifications' not in db.list_collection_names():
        db.create_collection('notifications')
        print("Created notifications collection")
    
    # Create indexes
    notifications_collection.create_index([("recipient_id", 1), ("is_read", 1)])
    notifications_collection.create_index([("created_at", -1)])
    print("Created notifications indexes")

def clean_existing_data(collections=None):
    """Remove all existing data from specified collections"""
    if collections is None:
        collections = [comments_collection, notifications_collection]
    
    for collection in collections:
        count = collection.count_documents({})
        result = collection.delete_many({})
        print(f"Deleted {result.deleted_count} of {count} documents from {collection.name}")

def generate_sample_notifications():
    """Generate realistic notification data"""
    users = list(users_collection.find())
    articles = list(articles_collection.find())
    
    if not users or not articles:
        print("Need both users and articles to generate notifications")
        return
    
    notification_types = ['article_post', 'follow']
    
    for i in range(len(users) * 3):  # ~3 notifications per user
        recipient = random.choice(users)
        sender = random.choice([u for u in users if u['_id'] != recipient['_id']])
        
        notif_type = random.choice(notification_types)
        
        if notif_type == 'article_post':
            article = random.choice(articles)
            source_id = article['_id']
            message = "commented on your article"
        else:
            source_id = sender['_id']
            message = f"{sender['username']} started following you"
        
        notification = {
            "recipient_id": recipient['_id'],
            "sender_id": sender['_id'],
            "sender_username": sender['username'],
            "notification_type": notif_type,
            "source_id": source_id,
            "message": message,
            "is_read": random.random() < 0.3,  # 30% chance of being read
            "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
            "read_at": datetime.now(timezone.utc) if random.random() < 0.3 else None
        }
        
        notifications_collection.insert_one(notification)
    
    print(f"Generated {notifications_collection.count_documents({})} notifications")


if __name__ == "__main__":
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Generate test comments for MongoDB articles')
    parser.add_argument('--clean', action='store_true', 
                        help='Remove all existing comments before generating new ones')
    parser.add_argument('--notifications', action='store_true',
                       help='Generate sample notifications')
    args = parser.parse_args()
    
    print(f"Connected to MongoDB at {MONGODB_URI}, using database {MONGODB_DB}")
    print("Starting comment generation process...")
    if args.clean:
        print("Clean mode activated - removing existing comments before generation")
    
    generate_test_comments(clean_first=args.clean)
    print("Verifying comment links...")
    verify_comment_links()
    print("Comment generation complete!")
    print(f"Connected to MongoDB at {MONGODB_URI}, using database {MONGODB_DB}")
    
    # Initialize collections
    initialize_notifications_collection()
    
    if args.clean:
        clean_existing_data()
    
    if args.notifications or not args.clean:
        print("Generating sample notifications...")
        generate_sample_notifications()
    
    # Keep existing comment generation logic
    print("Starting comment generation process...")
    generate_test_comments(clean_first=args.clean)
    print("Verifying comment links...")
    verify_comment_links()
    
    print("\nData generation complete!")
    print(f"- Articles: {articles_collection.count_documents({})}")
    print(f"- Comments: {comments_collection.count_documents({})}")
    print(f"- Notifications: {notifications_collection.count_documents({})}")