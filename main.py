import sys
import os
import json
import shutil
import logging

from git import Repo
from git.exc import GitCommandError

# Setting up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("script.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


def load_config(config_path):
    """Download config file"""
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file {config_path} not found")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Error reading JSON from configuration file: {e.msg}", e.doc, e.pos)


def update_repo(repo):
    '''
    We update the previously specified branch
    :param: repository
    :return:
    '''
    try:
        logging.info("Retrieving fresh data from a remote repository...")
        repo.git.fetch("--all")
        repo.git.pull()

        logging.info("Uploading files GIT LFS...")
        repo.git.lfs('pull')

        # Checking for the presence of LFS files before calling the check .gitattributes
        lfs_files = list_lfs_files(repo)
        if lfs_files:
            logging.info("Validation check .gitattributes...")
            check_gitattributes(repo.working_tree_dir, lfs_files)
        else:
            logging.info("There are no LFS files. Checking .gitattributes is not required.")

        logging.info("Data updated successfully.")
    except Exception as e:
        raise Exception(f"Error executing git pull: {e}")


def check_gitattributes(repo_path, lfs_files):
    """
    Checking the .gitattributes file and how it matches LFS files.
    :param repo_path: Path to local repository
    :param lfs_files: List of files monitored by LFS
    """
    gitattributes_path = os.path.join(repo_path, '.gitattributes')

    # Checking if .gitattributes exists
    if not os.path.exists(gitattributes_path):
        raise FileNotFoundError(".gitattributes not found in repository")

    # Reading the contents of .gitattributes
    with open(gitattributes_path, 'r') as file:
        gitattributes_lines = file.readlines()

    # Extracting patterns from .gitattributes
    tracked_patterns = set()
    for line in gitattributes_lines:
        if line.strip() and not line.startswith('#'):  # Ignore empty lines and comments
            pattern = line.split()[0]  # Take the first element of the line (path or pattern)
            tracked_patterns.add(pattern)

    # Checking that each LFS file is listed in .gitattributes
    missing_files = []
    for file in lfs_files:
        # Checking for the presence of the exact file name or corresponding pattern
        if not any(
                file == pattern or file.endswith(pattern.lstrip('*'))
                for pattern in tracked_patterns
        ):
            missing_files.append(file)

    if missing_files:
        raise ValueError(f"The following LFS files are missing from .gitattributes: {', '.join(missing_files)}")

    logging.info("The .gitattributes file is correct.")


def list_lfs_files(repo):
    """
    Getting a list of LFS files in the repository.
    :param repo:  Git repository
    :return: List of files monitored by LFS
    """
    try:
        lfs_files = repo.git.lfs("ls-files", "--name-only").splitlines()
        return lfs_files
    except GitCommandError as e:
        raise GitCommandError(f"Error when getting a list of LFS files: {e}")


def check_repo(repo_path, branch_name, repo_url, username, token):
    """Checking the local repository folder."""
    # Filtering system files
    content = [item for item in os.listdir(repo_path) if item != '.idea']

    if content:
        logging.info(f"Folder {repo_path} not empty.")
        try:
            repo = Repo(repo_path)
            # Swap Default Develop
            try:
                repo.git.checkout("-f", f"develop")
                logging.info("Switched to remote 'develop'")
            except Exception as error:
                logging.warning(f"Can't switch to local 'develop', trying another way...\nLog:{error} ")
                try:
                    repo.git.switch("-f", "develop")
                except Exception as error:
                    logging.warning(f"Can't switch to local 'develop',trying to get new one...\nLog:{error} ")
                try:
                    repo.git.switch("--track", "origin/develop")
                    update_repo(repo)
                except Exception as error:
                    logging.warning(f"Can't switch to remote 'develop', trying other way...\nLogs: {error}")
                try:
                    repo.git.checkout("-f", f"develop")
                except Exception as error:
                    logging.error(f"Can't switch to remote 'develop', tried #2, skip...\nLogs: {error}")
            # Done Swap
            repo.git.clean("-fd")
            repo.git.remote("update", "origin", "--prune")
            repo.git.reset("--hard")
            repo.git.gc("--prune=now")
            repo.git.fetch("--all")
            try:
                repo.git.pull()
                logging.info("Update current repository")
            except Exception as e:
                logging.warning(f"Can't update current repository\nWarn log: {e}")
            current_branch = repo.active_branch.name
            if current_branch == branch_name:
                logging.info("The branch in the local folder is the same as the specified branch. Pulling updates...")
                update_repo(repo)
            else:
                logging.info(f"Current branch: {current_branch}. Specified branch: {branch_name}.")
                # Checking if a branch exists locally
                if branch_name in [head.name for head in repo.heads]:
                    logging.info(f"Branch {branch_name} already exists locally. Let's switch and update it...")
                    try:
                        repo.git.switch("--track", f"{branch_name}")
                    except Exception as error1:
                        try:
                            repo.git.checkout("-f", f"{branch_name}")
                        except Exception as error2:
                            logging.critical(f"CRITICAL - Can't switch branche to local. Contact Administrator\nLogs: {error1}\n{error2}")
                            raise Exception("CRITICAL - Can't switch branche to local. Contact Administrator")
                    update_repo(repo)
                    return
                else:
                    # Cleaning...
                    logging.info("Cleaning repo branches...")
                    try:
                        for branch in repo.branches:
                            if branch.name not in [current_branch, branch_name, "develop"]:
                                try:
                                    repo.git.branch("-D", branch.name)
                                except Exception as error:
                                    logging.warning(f"Can't delete {branch.name} - Error: {error}")
                        logging.info("Cleaning complete...")
                    except Exception:
                        logging.warning("Can't succefully complete branch cleaning, skip...")
                    # Clean Ended
                    repo.git.reset("--hard")
                    logging.info(f"Getting branch {branch_name} from remote repository")
                    try:
                        repo.git.fetch("--all")
                        repo.git.reset("--hard")
                        try:
                            repo.git.checkout("-f", f"{branch_name}")
                        except Exception as error:
                            logging.warning(f"Can't make basic switch. Skip...\nLogs: {error}")
                            repo.git.switch("--track", f"{branch_name}")
                        logging.info(f"Created and switched to new branch: {branch_name}. Checking remote connection...")
                        update_repo(repo)
                        logging.info(f"Remote connection succefull.")
                        return
                    except Exception:
                        logging.error("Error: Can't make 'Light' switch to remote branch. Trying another way...")
                        try:
                            repo.git.reset("--hard")
                            repo.git.gc("--prune=now")
                            repo.git.checkout("-f", f"{branch_name}")
                        except Exception:
                            logging.critical("CRITICAL Error: Can't make 'Advanced' switch to remote branch. Contant Administrator")
                        raise Exception("CRITICAL Error accured with switch branches")

        except Exception:
            logging.critical("CRITICAL Error accured with switch branches")
            raise Exception("CRITICAL Error accured with switch branches")


def clone_repo(repo_url, branch_name, repo_path, username, token):
    """Cloning a repository with a specified branch."""
    # Forming a URL with credentials
    auth_repo_url = repo_url.replace("https://", f"https://{username}:{token}@")

    # Checking the presence of a directory for the repository
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)

    content = [item for item in os.listdir(repo_path) if item != '.idea']

    if content:
        check_repo(repo_path, branch_name, repo_url, username, token)
        return
    else:
        try:
            logging.info(f"First Cloning - Cloning branch '{branch_name}' from repository {repo_url} to {repo_path}...")
            repo = Repo.clone_from(auth_repo_url, repo_path, branch="develop")
            logging.info(f"The repository was successfully cloned to {repo_path}.")

            logging.info("Uploading files from GIT LFS")
            repo.git.lfs("pull")
            logging.info("LFS files uploaded successfully")

            # Checking for the presence of LFS files before calling the .gitattributes check
            lfs_files = list_lfs_files(repo)
            if lfs_files:
                logging.info("Checking the validity of .gitattributes...")
                check_gitattributes(repo.working_tree_dir, lfs_files)
            else:
                logging.info("There are no LFS files. No .gitattributes check required.")
            check_repo(repo_path, branch_name, repo_url, username, token)
            return

        except Exception as e:
            raise Exception(f"Error when cloning repository: {e}")

def save_config(config_path, config):
    """Saving changes to a configuration file."""
    try:
        with open(config_path, 'w') as file:
            json.dump(config, file, indent=4)
    except Exception as e:
        raise Exception(f"Error saving configuration file: {e}")


def force_remove_readonly(func, path, excinfo):
    os.chmod(path, 0o777)  # Removing the 'readonly' attribute
    func(path)  # Re-execute the delete operation


def clear_folder(folder_path):
    """Hard delete a folder and its contents, including hidden files and folders."""
    try:
        if os.path.exists(folder_path):
            # Recursively deleting a folder with error handling
            repo = Repo(folder_path)
            try:
                repo.git.clean("-fdx")
                repo.git.gc("--prune=now","--aggressive")
                repo.git.repack("-a", "-d", "--depth=250", "--window=250")
            except Exception as e:
                logging.warning(f"Can't clear folder {folder_path} - Error: {e}")
                shutil.rmtree(folder_path, onerror=force_remove_readonly)
                os.remove(folder_path)
            # = Old Clearning full delete
            #shutil.rmtree(folder_path, onerror=force_remove_readonly)
            #os.remove(folder_path)
            # =
            logging.info(f"Folder {folder_path} successfully cleared.")
    except Exception as e:
        logging.error(f"Error clearing folder {folder_path}: {e}. Let's try to continue")
        return


def get_repo_folder_name(repo_url):
    """Extract a folder name from the repository URL."""
    # Remove .git extension if present
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]

    # Extract the repository name from the URL
    repo_name = repo_url.split('/')[-1]

    # Clean the name to ensure it's a valid folder name
    repo_name = ''.join(c if c.isalnum() or c in ['-', '_'] else '_' for c in repo_name)

    return repo_name

def main():
    try:
        # Path to configuration file
        config_path = os.path.join(os.getcwd(), 'config.json')

        # Loading configuration
        config = load_config(config_path)

        # Getting parameters from the configuration
        bitbucket_config = config.get('bitbucket', {})
        username = bitbucket_config.get('username')
        token = bitbucket_config.get('token')

        paths_config = config.get('paths', {})
        base_repo_path = paths_config.get('repo_path')

        # Checking command line arguments
        if len(sys.argv) != 3:
            raise ValueError("Usage: python main.py <repository link> <branch name>")

        repo_url = sys.argv[1]
        branch_name = sys.argv[2]

        # Generate project-specific folder name
        repo_folder_name = get_repo_folder_name(repo_url)

        # Create project-specific repository path
        repo_path = os.path.join(base_repo_path, repo_folder_name) if base_repo_path else os.path.join(os.getcwd(), repo_folder_name)

        # Checking count_reset
        count_reset = config.get('count_reset', 0)
        if count_reset <= 0:
            # Reset again
            config['count_reset'] = 50
            save_config(config_path, config)

            logging.info('The attempts are over. Clear and continue.')
            clear_folder(repo_path)
        else:
            # Reduce count_reset by 1 and save the configs
            config['count_reset'] -= 1
            save_config(config_path, config)
            logging.info(f"Remaining attempts: {config['count_reset']}")

        if not username or not token:
            raise ValueError("Incorrect configuration. Check the config.json file.")

        # Cloning a repository
        clone_repo(repo_url, branch_name, repo_path, username, token)
    except Exception as e:
        raise Exception(f'Error: {e}')


if __name__ == "__main__":
    main()
