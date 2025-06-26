#!/usr/bin/env python3

import subprocess
import os
import argparse
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def run_git_command(command, check=True):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check,
            encoding='utf-8'
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing: {' '.join(command)}")
        print(f"  {e.stderr.strip()}")
        exit(1)
    except FileNotFoundError:
        print(f"❌ git command not found. Please ensure Git is installed and in your PATH.")
        exit(1)

def get_git_diff(staged=True, base_branch=None):
    if staged:
        # No need to run git add here, it should be done before calling
        return run_git_command(["git", "diff", "--cached"])
    elif base_branch:
        run_git_command(["git", "fetch", "origin", base_branch], check=False) # Update remote info
        return run_git_command(["git", "diff", f"origin/{base_branch}...HEAD"], check=False)
    return ""

def get_openai_suggestion(prompt, model="gpt-4o-mini", temperature=0.3):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip().replace("`", "")
    except Exception as e:
        print(f"❌ Error with OpenAI API: {e}")
        exit(1)

def generate_commit_message(diff, temperature=0.3, history=None, change_type=None):
    prompt = (
        f"You are an assistant that generates commit messages in the conventional commits format.\n"
        f"Based on the git diff below, generate a short, clear commit message in English.\n"
        f"The ENTIRE message MUST be in LOWERCASE.\n"
        f"Example: {change_type or 'feat'}: describe the change in lowercase.\n"
        f"Only the message, with no extra explanations or remarks."
    )

    if history:
        prompt += "\n\nCrucially, provide a different and unique suggestion from the ones I have already rejected:\n- " + "\n- ".join(history)

    prompt += f"\n\nDiff:\n{diff}"
    return get_openai_suggestion(prompt, temperature=temperature).lower()

def generate_pr_title(diff, temperature=0.4, history=None, **kwargs):
    prompt = (
        "You are an assistant that generates Pull Request titles in the conventional commits format.\n"
        "Based on the TOTAL git diff of a branch below, generate a comprehensive and concise PR title in English.\n"
        "Use a lowercase type prefix (e.g., 'feat:').\n"
        "The description after the type MUST start with a capital letter.\n"
        "Example: feat: Add user authentication and profile management.\n"
        "Generate ONLY the title, with no extra explanations or remarks."
    )
    if history:
        prompt += "\n\nCrucially, provide a different and unique suggestion from the ones I have already rejected:\n- " + "\n- ".join(history)

    prompt += f"\n\nDiff:\n{diff}"
    suggestion = get_openai_suggestion(prompt, temperature=temperature)
    
    parts = suggestion.split(':', 1)
    if len(parts) == 2:
        pr_type = parts[0].strip().lower()
        pr_desc = parts[1].strip()
        return f"{pr_type}: {pr_desc.capitalize()}"
    return suggestion

def generate_branch_name(diff, temperature=0.5, history=None, change_type=None):
    # This function remains the same
    pass # Placeholder for brevity

def user_interaction_loop(prompt_question, generation_function, diff, **kwargs):
    suggested_temperature = 0.5 if "branch" in prompt_question.lower() else 0.3
    previous_suggestions = []
    while True:
        suggestion = generation_function(
            diff,
            temperature=suggested_temperature,
            history=previous_suggestions,
            **kwargs
        )
        print(f"\n💬 {prompt_question}:\n{suggestion}")

        response = input("    ➡️ Accept? (Y) | 🔄 Regenerate? (r) | 🚫 Cancel? (n): ").strip().lower()

        if response in ('y', ''):
            return suggestion
        elif response == "r":
            if suggestion:
                previous_suggestions.append(suggestion)
            suggested_temperature = min(1.0, suggested_temperature + 0.2)
            print(f"ℹ️ Trying a different suggestion (temperature: {suggested_temperature:.1f})...")
            continue
        else:
            return None

def create_pull_request():
    print("\n🔄 Checking for GitHub CLI (gh)...")
    try:
        run_git_command(['gh', '--version'], check=True)
        print("✅ GitHub CLI is installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ GitHub CLI (gh) not found or not configured correctly.")
        print("   Please install it and authenticate with `gh auth login` to use the --pr feature.")
        return

    default_branch = ""
    try:
        head_branch_output = run_git_command(["git", "remote", "show", "origin"])
        for line in head_branch_output.splitlines():
            if 'HEAD branch' in line:
                default_branch = line.split(':')[1].strip()
                break
    except (subprocess.CalledProcessError, IndexError):
        pass

    if not default_branch:
        for branch in ["main", "master"]:
            try:
                run_git_command(["git", "show-ref", "--verify", f"refs/remotes/origin/{branch}"])
                default_branch = branch
                break
            except subprocess.CalledProcessError:
                continue
    
    if not default_branch:
        print("❌ Could not determine the default branch. Please create the PR manually.")
        return

    print(f"ℹ️ Using '{default_branch}' as the base branch for the PR.")
    full_diff = get_git_diff(staged=False, base_branch=default_branch)

    if not full_diff:
        print("✅ No differences found between your branch and the default branch. Nothing to create a PR for.")
        return

    pr_title = user_interaction_loop("Suggested PR Title", generate_pr_title, full_diff)

    if not pr_title:
        print("🚫 PR creation canceled by user.")
        return

    commits_list = run_git_command(["git", "log", f"origin/{default_branch}..HEAD", "--pretty=format:- %s"], check=False).splitlines()
    pr_body = "\n".join(["## Commits in this PR"] + commits_list)

    print("\n🚀 Creating Pull Request...")
    pr_command = ['gh', 'pr', 'create', '--title', pr_title, '--body', pr_body]
    pr_output = run_git_command(pr_command, check=True)
    print(f"✅ Pull Request created successfully:\n{pr_output}")

def main():
    parser = argparse.ArgumentParser(description="Generates commits and branches with AI.")
    parser.add_argument("--branch", "-b", action="store_true", help="Request the generation of a branch name.")
    parser.add_argument("--pr", action="store_true", help="Create a pull request on GitHub.")
    parser.add_argument("--type", "-t", type=str, choices=['feat', 'fix'], help="Specify the type of change (feat or fix).")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set.")
        exit(1)

    run_git_command(["git", "add", "."])
    staged_diff = get_git_diff(staged=True)

    if not staged_diff:
        if args.pr:
            print("ℹ️ No staged changes. Proceeding to create a Pull Request for existing commits.")
            create_pull_request()
            exit(0)
        else:
            print("✅ No staged changes found. Nothing to commit.")
            exit(0)

    # Branching and committing logic
    original_branch_name = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    new_branch_created = False
    if args.branch:
        branch_name = user_interaction_loop("Suggested branch name", generate_branch_name, staged_diff, change_type=args.type)
        if branch_name:
            if branch_name != original_branch_name:
                run_git_command(["git", "checkout", "-b", branch_name], check=False)
                new_branch_created = True
                print(f"✅ Switched to new branch '{branch_name}'.")
            else:
                 print(f"⚠️ Already on branch '{branch_name}'.")
        else:
            print("🚫 Branch creation canceled.")

    commit_message = user_interaction_loop("Suggested commit message", generate_commit_message, staged_diff, change_type=args.type)

    if commit_message:
        print("💾 Committing...")
        run_git_command(["git", "commit", "-m", commit_message])
        branch_to_push = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        print(f"🚀 Pushing to branch '{branch_to_push}'...")
        run_git_command(["git", "push", "--set-upstream", "origin", branch_to_push])
        print("✨ Success!")

        if args.pr:
            create_pull_request()
    else:
        print("🚫 Commit canceled.")
        # Logic to checkout back to original branch if needed
        if new_branch_created:
            go_back = input(f"❓ Return to original branch '{original_branch_name}'? (y/N): ").strip().lower()
            if go_back == 'y':
                run_git_command(["git", "checkout", original_branch_name])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🚫 Operation canceled by user. Exiting.")
        exit(130)
