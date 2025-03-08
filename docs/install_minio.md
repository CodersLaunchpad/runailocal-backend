MinIO Setup Guide for Mac and Windows

Windows Installation

Step 1: Download MinIO

Download the MinIO executable for Windows from the following URL:

https://dl.min.io/server/minio/release/windows-amd64/minio.exe

Step 2: Prepare the Environment

Create a folder where MinIO will store data, for example, C:\minio

Move the downloaded minio.exe file to a convenient location on your system

Step 3: Run MinIO Server

Open PowerShell or Command Prompt

Navigate to the directory containing minio.exe or add its path to the system $PATH

Run the following command to start MinIO:

.\minio.exe server C:\minio --console-address :9001

Replace C:\minio with your desired data storage path.

Step 4: Access MinIO

Once the server starts, the console will display output similar to:

API: http://192.0.2.10:9000 http://127.0.0.1:9000
RootUser: minioadmin
RootPass: minioadmin
Console: http://192.0.2.10:9001 http://127.0.0.1:9001

Open a web browser and go to http://127.0.0.1:9001 to access the MinIO Console

Log in using the default credentials:

Username: minioadmin

Password: minioadmin

Mac Installation

Step 1: Install MinIO

You can install MinIO using Homebrew:

brew install minio/stable/minio

Step 2: Create a Data Directory

Create a directory where MinIO will store data:

mkdir -p ~/minio_data

Step 3: Run MinIO Server

Start MinIO using the following command:

minio server ~/minio_data --console-address :9001

Step 4: Access MinIO

Once the server starts, the console will display API and Console endpoints:

API: http://127.0.0.1:9000
RootUser: minioadmin
RootPass: minioadmin
Console: http://127.0.0.1:9001

Open a web browser and go to http://127.0.0.1:9001

Log in using the default credentials:

Username: minioadmin

Password: minioadmin

Optional: Set Up MinIO Client (mc)

To manage MinIO from the command line, install MinIO Client (mc):

Windows

Download mc.exe from:

https://dl.min.io/client/mc/release/windows-amd64/mc.exe

Mac

Install mc using Homebrew:

brew install minio/stable/mc

Configure MinIO Client

Run the following command to configure mc:

mc alias set local http://127.0.0.1:9000 minioadmin minioadmin

You can now use mc commands to interact with MinIO, e.g.,

mc ls local