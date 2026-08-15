import os
import git

REPO_URL = os.environ.get("GITHUB_PROXY", "") + "https://github.com/aloshdenny/reverse-SynthID.git"
REPO_BRANCH = 'b11083676fd3ee3ff97ce9d03c0e409e46905902'
LOCAL_PATH = os.path.abspath("./reverse-SynthID")

def install_src():
    if not os.path.exists(LOCAL_PATH):
        print(f"Cloning repository from {REPO_URL}@{REPO_BRANCH} to {LOCAL_PATH}...")
        repo = git.Repo.clone_from(REPO_URL, LOCAL_PATH)
        repo.git.checkout(REPO_BRANCH)
        print(f"Repository cloned to {LOCAL_PATH}")
    else:
        print(f"Repository already exists at {LOCAL_PATH}")
