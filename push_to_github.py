#!/usr/bin/env python3
"""Create GitHub repository and push code"""
import subprocess
import sys
import os

def create_and_push():
    print("=" * 70)
    print("GITHUB REPOSITORY SETUP")
    print("=" * 70)
    
    repo_name = input("\nEnter repository name (default: vosk-transcription): ").strip()
    if not repo_name:
        repo_name = "vosk-transcription"
    
    is_private = input("Make repository private? (y/N): ").strip().lower() == 'y'
    visibility = "private" if is_private else "public"
    
    github_username = input("\nEnter your GitHub username: ").strip()
    github_token = input("Enter your GitHub Personal Access Token: ").strip()
    
    if not github_username or not github_token:
        print("[ERROR] Username and token are required!")
        return False
    
    print(f"\n[1/3] Creating {visibility} repository '{repo_name}' on GitHub...")
    
    # Create repository using GitHub API
    import urllib.request
    import json
    
    data = {
        "name": repo_name,
        "description": "Voice-to-text transcription system using Vosk with MP3 support",
        "private": is_private,
        "auto_init": False
    }
    
    try:
        req = urllib.request.Request(
            "https://api.github.com/user/repos",
            data=json.dumps(data).encode('utf-8'),
            headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"[OK] Repository created: {result['html_url']}")
            repo_url = result['clone_url'].replace("https://", f"https://{github_username}:{github_token}@")
            
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        print(f"[ERROR] Failed to create repository: {error_msg}")
        return False
    
    print(f"\n[2/3] Adding remote origin...")
    subprocess.run(["git", "remote", "add", "origin", repo_url], 
                   capture_output=True)
    
    print(f"[3/3] Pushing to GitHub...")
    result = subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"[OK] Successfully pushed to GitHub!")
        print(f"\n{result.stdout}")
        print(f"\n✓ Repository URL: https://github.com/{github_username}/{repo_name}")
        return True
    else:
        print(f"[ERROR] Push failed: {result.stderr}")
        return False

if __name__ == "__main__":
    success = create_and_push()
    sys.exit(0 if success else 1)
