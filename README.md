# Setup and Run The Project

This README provides instructions on how to set up the virtual environment, install the required packages, set up MinIO, and run the application.

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- MinIO Server (for object storage)

## Setup Instructions

### Step 1: Clone the Repository

Clone or download this repository to your local machine.

### Step 2: Create a Virtual Environment

#### Windows
```bash
# Navigate to the project directory
cd project-directory

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate
```

#### Mac/Linux
```bash
# Navigate to the project directory
cd project-directory

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### Step 3: Install Requirements

Once the virtual environment is activated, install the required packages:

```bash
pip install -r requirements.txt
```

### Step 4: Set Up MinIO

MinIO is an object storage server compatible with Amazon S3. Follow these steps to set it up:

#### Windows

1. Download the MinIO Server for Windows from the [official MinIO website](https://min.io/download)
2. Create a directory for MinIO data:
```bash
mkdir C:\minio\data
```
3. Start MinIO Server:
```bash
minio.exe server C:\minio\data --console-address ":9001"
```

#### macOS

1. Install MinIO using Homebrew:
```bash
brew install minio/stable/minio
```
2. Create a directory for MinIO data:
```bash
mkdir -p ~/minio/data
```
3. Start MinIO Server:
```bash
minio server ~/minio/data --console-address ":9001"
```

4. Access the MinIO Console at http://localhost:9001 and set up your access credentials

### Step 5: Set Up Environment Variables

The project uses environment variables for configuration. You need to create a `.env` file based on the provided template:

1. Make a copy of the `.env.example` file and rename it to `.env`:

#### Windows
```bash
copy .env.example .env
```

#### Mac/Linux
```bash
cp .env.example .env
```

2. Open the `.env` file in a text editor and fill in the required values for all environment variables, including the MinIO credentials:
```
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
MINIO_BUCKET_NAME=your_bucket_name
MINIO_SECURE=False
```

### Step 6: Run the Application

After installing all requirements and setting up MinIO, you can run the application:

```bash
python main.py
```

## Deactivating the Virtual Environment

When you're done working on the project, you can deactivate the virtual environment:

#### Windows/Mac/Linux
```bash
deactivate
```

## Troubleshooting

If you encounter any issues:

1. Ensure you have the correct Python version installed
2. Make sure the virtual environment is activated before installing requirements
3. Check that all the required packages are listed in requirements.txt
4. Verify that MinIO server is running and accessible
5. Ensure your MinIO credentials in the `.env` file are correct

For further assistance, reach out on whatsapp.