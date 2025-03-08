# Installing MongoDB Locally on a MacBook

[Source](https://dev.to/saint_vandora/how-to-install-mongodb-locally-on-a-macbook-5h3a)

This guide provides step-by-step instructions for installing MongoDB on your MacBook using Homebrew.

## Prerequisites

- Ensure you have [Homebrew](https://brew.sh/) installed on your Mac. If not, follow the instructions below to install it.

## Step 1: Install Homebrew

Homebrew is a popular package manager for macOS that simplifies the installation of software. To install Homebrew, run the following command in your Terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Step 2: Update Homebrew and Tap the MongoDB Formula

It's a good practice to ensure that your Homebrew is up-to-date. Additionally, you need to tap the MongoDB repository to get the latest versions:

```bash
brew update
brew tap mongodb/brew
```

## Step 3: Install MongoDB

With Homebrew updated and the MongoDB formula tapped, you can now install MongoDB. Execute the following command in your Terminal:

```bash
brew install mongodb-community
```

## Step 4: Start MongoDB

After the installation, you can start MongoDB as a background service. This ensures that it starts automatically at login and continues running in the background:

```bash
brew services start mongodb/brew/mongodb-community
```

## Step 5: Verify the Installation

To ensure that MongoDB is installed correctly and running, connect to the MongoDB shell. Open the Terminal and type:

```bash
mongosh
```

If MongoDB is running, this command will open the MongoDB shell, allowing you to interact with the database. If you see the MongoDB shell prompt, the installation was successful.

## Step 6: Stop MongoDB

If you need to stop MongoDB for maintenance or system updates, you can stop the service with the following command:

```bash
brew services stop mongodb/brew/mongodb-community
```

## Additional Information

- **Configuration File**: The default configuration file for MongoDB is located at `/usr/local/etc/mongod.conf`.
- **Data Files**: MongoDB stores its data files in `/usr/local/var/mongodb`.
- **Log Files**: MongoDB log files are stored in `/usr/local/var/log/mongodb`.

These paths are the default locations, but you can customize them by editing the configuration file.

## Uninstalling MongoDB

If you ever need to uninstall MongoDB, you can do so easily with Homebrew:

```bash
brew services stop mongodb/brew/mongodb-community
brew uninstall mongodb/brew/mongodb-community
```

These commands stop the MongoDB service and remove the MongoDB installation from your system.

## Summary of Commands

Here’s a summary of the commands you’ll use to install, start, stop, and verify MongoDB on your MacBook:

```bash
# Install Homebrew (if not already installed)
bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Update Homebrew and tap MongoDB
brew update
brew tap mongodb/brew

# Install MongoDB
brew install mongodb-community

# Start MongoDB as a service
brew services start mongodb/brew/mongodb-community

# Verify installation by opening MongoDB shell
mongosh

# Stop MongoDB service
brew services stop mongodb/brew/mongodb-community
```
```

### Key Changes Made:
- **Headings**: Added headings for each step to improve navigation.
- **Code Blocks**: Used code blocks for commands to enhance readability.
- **Bullet Points**: Used bullet points for additional information to make it easier to digest.
- **Summary Section**: Included a summary of commands at the end for quick reference.

This format is more suitable for a README file, making it easier for users to follow the installation process.