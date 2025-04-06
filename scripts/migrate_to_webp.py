import asyncio
import io
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from PIL import Image
from minio import Minio
import motor.motor_asyncio
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Load environment variables
# load_dotenv()

# Configuration
MINIO_ENDPOINT = os.getenv("MINIO_SERVER", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_USERNAME", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "rail")
MONGO_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("DATABASE_NAME", "cms")

# Initialize MinIO client
def get_minio_client():
    return Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

# Initialize MongoDB client
def get_mongo_client():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    return client[MONGO_DB]

async def process_image(image_data: bytes, max_size: tuple = (1920, 1080), quality: int = 85) -> bytes:
    """
    Process and compress an image, converting it to WebP format
    """
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if larger than max_size while maintaining aspect ratio
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save as WebP
        output = io.BytesIO()
        image.save(output, format='WEBP', quality=quality, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        raise

async def migrate_file(file_doc: Dict[str, Any], minio_client: Minio, db) -> bool:
    """
    Migrate a single file to WebP format
    Returns True if successful, False otherwise
    """
    try:
        file_id = file_doc["file_id"]
        object_name = file_doc["object_name"]
        print(f"\nProcessing file: {object_name}")
        
        # Skip if already migrated
        if file_doc.get("migrated_at"):
            print(f"Skipping already migrated file: {object_name}")
            return True
            
        # Download the original file from MinIO
        print(f"Downloading file from MinIO...")
        response = minio_client.get_object(MINIO_BUCKET, object_name)
        original_data = response.read()
        
        # Process the image
        print(f"Converting to WebP...")
        processed_data = await process_image(original_data)
        
        # Create new object name with .webp extension
        new_object_name = os.path.splitext(object_name)[0] + '.webp'
        
        # Upload the processed file back to MinIO
        print(f"Uploading processed file to MinIO...")
        minio_client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=new_object_name,
            data=io.BytesIO(processed_data),
            length=len(processed_data),
            content_type='image/webp'
        )
        
        # Generate new URL with proper timedelta
        new_url = minio_client.presigned_get_object(
            bucket_name=MINIO_BUCKET,
            object_name=new_object_name,
            expires=timedelta(hours=1)
        )
        
        # Update MongoDB document
        print(f"Updating MongoDB record...")
        await db.files.update_one(
            {"file_id": file_id},
            {
                "$set": {
                    "filename": os.path.splitext(file_doc["filename"])[0] + '.webp',
                    "file_type": "image/webp",
                    "file_extension": "webp",
                    "file_url": new_url,
                    "size": len(processed_data),
                    "object_name": new_object_name,
                    "migrated_at": datetime.utcnow()
                }
            }
        )
        
        print(f"Successfully migrated {object_name}")
        return True
        
    except Exception as e:
        print(f"Error migrating file {file_doc.get('object_name', 'unknown')}: {str(e)}")
        return False

async def main():
    """
    Main function to migrate all images to WebP format
    """
    try:
        # Initialize clients
        minio_client = get_minio_client()
        db = get_mongo_client()
        
        # Get all image files from MongoDB
        print("Fetching image files from MongoDB...")
        image_files = await db.files.find({
            "file_type": {"$regex": "^image/"}
        }).to_list(length=None)
        
        total_files = len(image_files)
        print(f"Found {total_files} image files to process")
        
        # Process each file
        successful = 0
        failed = 0
        skipped = 0
        
        for index, file_doc in enumerate(image_files, 1):
            print(f"\nProcessing file {index}/{total_files}")
            try:
                result = await migrate_file(file_doc, minio_client, db)
                if result:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error processing file: {str(e)}")
                failed += 1
        
        print("\nMigration Summary:")
        print(f"Total files processed: {total_files}")
        print(f"Successfully migrated: {successful}")
        print(f"Failed to migrate: {failed}")
        print(f"Skipped (already migrated): {skipped}")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 