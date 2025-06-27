#!/usr/bin/env python3

import subprocess
import os
import argparse
import sys
from openai import OpenAI
from dotenv import load_dotenv
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

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
        return run_git_command(["git", "diff", "--cached"])
    elif base_branch:
        run_git_command(["git", "fetch", "origin", base_branch], check=False)
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
    if change_type:
        prompt = prompt.replace("{change_type or 'feat'}", change_type)

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

def generate_pr_body(diff, change_type, temperature=0.5):
    pr_section_title = "Feature" if change_type == 'feat' else "Correção"
    prompt = f"""**Sua Tarefa:**
Você é um Engenheiro de Software Sênior e sua tarefa é gerar uma descrição de Pull Request (PR) completa, técnica e profissional em formato Markdown.

**Instruções:**
- A descrição deve ser baseada no tipo de alteração e no diff de código fornecidos.
- Escreva sempre em português do Brasil.
- Seja objetivo e técnico, mas evite jargões desnecessários.
- O resultado final deve ser um documento Markdown limpo e bem formatado.
- NÃO inclua as instruções, o tipo de alteração ou o diff do código na sua resposta final.
- O resultado DEVE começar diretamente com o cabeçalho da primeira seção (`## {pr_section_title}`), sem nenhum texto, ```markdown``` ou qualquer outra marcação antes dele.

**Tipo de Alteração:**
{change_type}

**Diff do Código:**
```diff
{diff}
```

**Estrutura da Descrição do PR (use exatamente este formato):**

## {pr_section_title}
(Resuma em uma frase o que foi corrigido ou implementado.)

## Descrição do Problema
(Descreva o cenário anterior à mudança: o que estava quebrado, ausente ou poderia ser melhorado?)

## Solução Implementada
(Explique as alterações técnicas de forma clara. Detalhe a nova lógica, as camadas modificadas (controllers, services, etc.) e quaisquer refatorações importantes.)

## Impacto Esperado
(Descreva o resultado esperado após a implementação. Como a solução resolve o problema e qual o comportamento esperado em produção?)
"""
    return get_openai_suggestion(prompt, model="gpt-4o-mini", temperature=temperature)

def generate_branch_name(diff, temperature=0.5, history=None, change_type=None):
    prompt = (
        "You are an assistant that generates Git branch names.\n"
        "Based on the git diff below, generate a short and descriptive branch name in English.\n"
        "The branch name MUST follow the format: type/short-description-in-kebab-case.\n"
    )
    if change_type:
        prompt += f"The type MUST be '{change_type}'.\n"
        prompt += f"Example: {change_type}/add-user-authentication.\n"
    else:
        prompt += "Infer the type from the diff. Use one of the following types: 'feat', 'fix', 'chore', 'docs', 'refactor', 'style', 'test'.\n"
        prompt += "Example: feat/add-user-authentication.\n"

    prompt += "Generate ONLY the branch name, with no extra explanations or remarks."

    if history:
        prompt += "\n\nCrucially, provide a different and unique suggestion from the ones I have already rejected:\n- " + "\n- ".join(history)

    prompt += f"\n\nDiff:\n{diff}"
    
    suggestion = get_openai_suggestion(prompt, temperature=temperature)
    return suggestion.strip()

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
        print(f"\n{prompt_question}:\n{suggestion}")

        response = input("    ➡️ Accept? (Y) | 🔄 Regenerate? (r) | 🚫 Cancel? (n): ").strip().lower()

        if response in ('y', ''):
            return suggestion
        elif response == "r":
            if suggestion:
                previous_suggestions.append(suggestion)
            suggested_temperature = min(1.0, suggested_temperature + 0.2)
            print("🔄 Regenerating...")
            continue
        else:
            return None

def create_pull_request(change_type=None):
    try:
        run_git_command(['gh', '--version'], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ GitHub CLI (gh) not found or not configured correctly.")
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

    full_diff = get_git_diff(staged=False, base_branch=default_branch)

    if not full_diff:
        print("✅ No differences found to create a PR.")
        return

    if not change_type:
        change_type = inquirer.select(
            message="Select the type of change for the PR:",
            choices=[
                Choice(value="feat", name="feat - A new feature"),
                Choice(value="fix", name="fix - A bug fix"),
            ],
            default="feat",
            vi_mode=True,
        ).execute()

    pr_title = user_interaction_loop("Suggested PR Title", generate_pr_title, full_diff)
    if not pr_title:
        print("🚫 PR title generation canceled.")
        return

    # Extract change type from the final PR title to ensure consistency
    body_change_type = change_type
    if ':' in pr_title:
        title_prefix = pr_title.split(':', 1)[0].strip().lower()
        if title_prefix in ['feat', 'fix']:
            body_change_type = title_prefix

    print("🤖 Generating PR description...")
    pr_body = generate_pr_body(full_diff, body_change_type)

    print("🚀 Creating PR...")
    pr_command = ['gh', 'pr', 'create', '--title', pr_title, '--body', pr_body]
    pr_output = run_git_command(pr_command, check=True)
    print(f"✅ PR created: {pr_output}")

def main():
    parser = argparse.ArgumentParser(description="Generates commits and branches with AI.")
    parser.add_argument("--branch", "-b", action="store_true", help="Request the generation of a branch name.")
    parser.add_argument("--pr", action="store_true", help="Create a pull request on GitHub.")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set.")
        exit(1)

    run_git_command(["git", "add", "."])
    staged_diff = get_git_diff(staged=True)

    change_type = None
    if staged_diff:
        change_type = inquirer.select(
            message="Select the type of change:",
            choices=[
                Choice(value=None, name="auto - Let AI detect the type"),
                Choice(value="feat", name="feat - A new feature"),
                Choice(value="fix", name="fix - A bug fix"),
            ],
            default=None,
            vi_mode=True,
        ).execute()

        # Branching and committing logic
        original_branch_name = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        new_branch_created = False
        if args.branch:
            branch_name = user_interaction_loop("Suggested branch name", generate_branch_name, staged_diff, change_type=change_type)
            if branch_name and branch_name != original_branch_name:
                run_git_command(["git", "checkout", "-b", branch_name], check=False)
                new_branch_created = True
                print(f"✅ Switched to '{branch_name}'.")
            elif not branch_name:
                print("🚫 Branch creation canceled.")

        commit_message = user_interaction_loop("Suggested commit message", generate_commit_message, staged_diff, change_type=change_type)

        if commit_message:
            print("💾 Committing...")
            run_git_command(["git", "commit", "-m", commit_message])
            branch_to_push = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            print(f"🚀 Pushing to '{branch_to_push}'...")
            run_git_command(["git", "push", "--set-upstream", "origin", branch_to_push])
            print("✅ Pushed successfully.")

            if args.pr:
                create_pull_request(change_type)
        else:
            print("🚫 Commit canceled.")
            if new_branch_created:
                go_back = input(f"❓ Return to '{original_branch_name}'? (y/N): ").strip().lower()
                if go_back == 'y':
                    run_git_command(["git", "checkout", original_branch_name])
    elif args.pr:
        print("ℹ️ No staged changes. Creating PR from existing commits.")
        create_pull_request()
    else:
        print("✅ No staged changes.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🚫 Operation canceled by user. Exiting.")
        exit(130)
