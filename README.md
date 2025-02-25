# Setup and Run The Project

This README provides instructions on how to set up the virtual environment, install the required packages, and run the application.

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

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

### Step 4: Set Up Environment Variables

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

2. Open the `.env` file in a text editor and fill in the required values for all environment variables.

### Step 5: Run the Application

After installing all requirements, you can run the application:

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

For further assistance, reach out on whatsapp.