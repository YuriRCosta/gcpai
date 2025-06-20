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

def get_git_diff():
    run_git_command(["git", "add", "."])
    diff = run_git_command(["git", "diff", "--cached"])
    return diff

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

def generate_commit_message(diff, temperature=0.3, history=None):
    prompt = (
        "You are an assistant that generates commit messages in the conventional commits format.\n"
        "Based on the git diff below, identify the MOST SIGNIFICANT change and generate a short, clear commit message in English about it.\n"
        "Focus on the main purpose of the change.\n"
        "Use prefixes like feat, fix, chore, refactor, test, docs, style, perf, ci, build, revert etc.\n"
        "Only the message, with no extra explanations or remarks.\n"
        "Generate ONLY ONE commit message, with no line breaks or special formatting.\n"
        "Nothing but a commit message."
    )
    if history:
        history_prompt = "\n\nCrucially, provide a different and unique suggestion from the ones I have already rejected:\n- "
        history_prompt += "\n- ".join(history)
        prompt += history_prompt

    prompt += f"\n\nDiff:\n{diff}"
    return get_openai_suggestion(prompt, temperature=temperature)

def generate_branch_name(diff, temperature=0.5, history=None):
    prompt = (
        "You are an assistant that generates Git branch names.\n"
        "Based on the git diff below, identify the MOST SIGNIFICANT change and generate a short, descriptive branch name in English for it, "
        "using hyphens to separate words and following the 'type/short-description' format.\n"
        "The name should reflect the main purpose of the changes.\n"
        "Use prefixes like feat/, fix/, chore/, refactor/, test/, docs/, style/, perf/, ci/, build/, revert/.\n"
        "Examples: feat/add-user-login, fix/resolve-payment-bug, chore/update-dependencies.\n"
        "Generate ONLY the branch name, with no extra explanations or remarks."
    )
    if history:
        history_prompt = "\n\nCrucially, provide a different and unique suggestion from the ones I have already rejected:\n- "
        history_prompt += "\n- ".join(history)
        prompt += history_prompt

    prompt += f"\n\nDiff:\n{diff}"
    return get_openai_suggestion(prompt, temperature=temperature)

def user_interaction_loop(prompt_question, generation_function, diff):
    if "branch" in prompt_question.lower():
        suggested_temperature = 0.5
    else:
        suggested_temperature = 0.3

    previous_suggestions = []
    while True:
        suggestion = generation_function(
            diff,
            temperature=suggested_temperature,
            history=previous_suggestions
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

def open_in_browser(url):
    command = []
    if sys.platform.startswith('linux'):
        command = ['xdg-open', url]
    elif sys.platform == 'darwin':
        command = ['open', url]
    elif sys.platform == 'win32':
        command = ['start', url]
    
    if not command:
        return False

    try:
        # Usamos DEVNULL para suprimir qualquer saída do comando
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_pr_url(branch_name):
    try:
        remote_url = run_git_command(["git", "config", "--get", "remote.origin.url"])
        if not remote_url:
            return None

        if remote_url.startswith("https://"):
            repo_path = remote_url.replace("https://github.com/", "").replace(".git", "")
        elif remote_url.startswith("git@"):
            repo_path = remote_url.replace("git@github.com:", "").replace(".git", "")
        else:
            return None

        return f"https://github.com/{repo_path}/pull/new/{branch_name}"
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description="Generates commits and branches with AI.")
    parser.add_argument("--branch", "-b", action="store_true", help="Request the generation of a branch name.")
    parser.add_argument("--pr", action="store_true", help="Open a pull request in the browser after a successful push.")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set.")
        print("   Please define it in your .env file or your environment.")
        exit(1)

    diff = get_git_diff()

    if not diff:
        print("✅ No staged changes found. Nothing to commit.")
        exit(0)

    branch_name = None
    new_branch_created = False
    original_branch_name = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    if args.branch:
        branch_name = user_interaction_loop("Suggested branch name", generate_branch_name, diff)
        if branch_name:
            if branch_name == original_branch_name:
                print(f"⚠️ The suggested branch ('{branch_name}') is the same as the current branch. No new branch will be created.")
                new_branch_created = False
            else:
                print(f"🌿 Creating and checking out branch '{branch_name}'...")
                run_git_command(["git", "checkout", "-b", branch_name], check=False)
                current_branch_check = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
                if current_branch_check == branch_name:
                    new_branch_created = True
                    print(f"✅ Switched to new branch '{branch_name}'.")
                else:
                    print(f"⚠️ Could not create or switch to branch '{branch_name}'. Check if it already exists or if there are conflicts.")
                    print(f"   Continuing on branch '{original_branch_name}'.")
                    branch_name = None
        else:
            print("🚫 Branch creation canceled. Continuing on the current branch.")

    commit_message = user_interaction_loop("Suggested commit message", generate_commit_message, diff)

    if commit_message:
        print(f"\n📝 Commit Review:")
        print(f"   Message: \"{commit_message}\"")

        branch_to_commit_on = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if new_branch_created and branch_name:
            print(f"   Branch: {branch_name} (new)")
        else:
            print(f"   Branch: {branch_to_commit_on} (current)")

        confirmation = input("\n✅ Proceed with commit and push? (Y/n): ").strip().lower()

        if confirmation in ('y', ''):
            print("💾 Committing...")
            run_git_command(["git", "commit", "-m", commit_message])

            branch_to_push = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            print(f"🚀 Pushing to branch '{branch_to_push}'...")

            if new_branch_created and branch_to_push == branch_name:
                run_git_command(["git", "push", "--set-upstream", "origin", branch_to_push])
            else:
                run_git_command(["git", "push", "origin", branch_to_push])
            
            print("✨ Success!")

            if args.pr:
                pr_url = get_pr_url(branch_to_push)
                if pr_url:
                    open_pr_response = input(f"\n🔗 Would you like to open a Pull Request in your browser? (Y/n): ").strip().lower()
                    if open_pr_response in ('y', ''):
                        print(f"🚀 Opening PR link in your browser...")
                        if not open_in_browser(pr_url):
                            print(f"⚠️ Could not open the browser automatically.")
                            print(f"   Please, copy and paste this URL:\n   {pr_url}")
        else:
            print("🚫 Operation canceled by the user.")
            if new_branch_created and branch_name != original_branch_name:
                go_back = input(f"❓ You created the branch '{branch_name}'. Would you like to return to the original branch '{original_branch_name}'? (y/N): ").strip().lower()
                if go_back == 'y':
                    print(f"↪️ Returning to branch '{original_branch_name}'...")
                    run_git_command(["git", "checkout", original_branch_name])
                    print(f"✅ Returned to '{original_branch_name}'.")
                else:
                    print(f"ℹ️ Staying on branch '{branch_name}'.")
    else:
        print("🚫 Commit canceled.")
        if new_branch_created and branch_name != original_branch_name:
            go_back = input(f"❓ You created the branch '{branch_name}' but canceled the commit. Would you like to return to the original branch '{original_branch_name}'? (y/N): ").strip().lower()
            if go_back == 'y':
                print(f"↪️ Returning to branch '{original_branch_name}'...")
                run_git_command(["git", "checkout", original_branch_name])
                print(f"✅ Returned to '{original_branch_name}'.")
            else:
                print(f"ℹ️ Staying on branch '{branch_name}'.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🚫 Operation canceled by user. Exiting.")
        exit(130)
