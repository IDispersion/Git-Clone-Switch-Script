# 🚀 Git Clone & Switch Python Script

This script automatically clones a specified Git repository and switches to the desired branch. Perfectly use in CICD for PC workers with remote and big repository.

## 📌 Features
- Clone a remote repository
- Switch to the specified branch
- Automatically update the branch from `origin`
- Creates project-specific folders based on repository URL

## 🔧 Installation and Usage

### 1️⃣ Download the script

### 2️⃣ Configure the script
Create a `config.json` file in the same directory as the script with the following structure:
```json
{
  "bitbucket": {
    "username": "your_username",
    "token": "your_token"
  },
  "paths": {
    "repo_path": "/path/to/base/directory"  // Optional: Base directory for all repositories
  },
  "count_reset": 50
}
```

If `repo_path` is provided, project-specific folders will be created inside this directory.
If `repo_path` is not provided, project-specific folders will be created in the current working directory.

### 3️⃣ Run the script
```bash
./main.py <repository_clone_link> <branch>
```

#### Example:
```bash
./main.py https://github.com/example/project.git develop
```

This will clone the repository into a folder named `project` inside the base directory specified in `config.json` (or in the current directory if no base directory is specified).

## 🛠 Requirements
- Git installed (`git --version`)
- Access to the remote repository

## 📜 License
**Under work...**

## 📬 Contact
If you have any questions or suggestions, create an issue or contact me via email: [samedi.ary@yahoo.com](mailto:samedi.ary@yahoo.com).
