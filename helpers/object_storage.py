from minio import Minio
import io
from PIL import Image

def upload_image(minio_client: Minio, bucket_name, file_path, object_name):
    """
    Uploads an image to MinIO.

    :param minio_client: MinIO client instance
    :param bucket_name: Name of the MinIO bucket
    :param file_path: Local file path of the image
    :param object_name: Name to be saved in MinIO
    """
    try:
        minio_client.fput_object(bucket_name, object_name, file_path)
        print(f"Successfully uploaded {file_path} as {object_name}")
    except Exception as e:
        print(f"Error uploading file: {e}")


def read_image(minio_client: Minio, bucket_name, object_name):
    """
    Reads an image from MinIO and loads it into memory.

    :param minio_client: MinIO client instance
    :param bucket_name: Name of the MinIO bucket
    :param object_name: Name of the object in MinIO
    :return: PIL Image object
    """
    try:
        response = minio_client.get_object(bucket_name, object_name)
        image = Image.open(io.BytesIO(response.read()))
        return image
    except Exception as e:
        print(f"Error reading image: {e}")
        return None
