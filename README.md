# Git AI Assistant

A command-line tool to streamline your Git workflow using AI.

## Features

- ✨ AI-powered suggestions for conventional commit messages.
- 🌿 Smart generation of descriptive branch names.
- 🚀 Full workflow automation: stage, commit, push, and optionally open a pull request.
- 💬 Interactive loop to refine suggestions until they are perfect.

## Prerequisites

- Git
- Python 3.8+

## Installation

This project includes an automated installation script that handles all setup.

1. **Clone the repository:**

   ```bash
   git clone https://github.com/YuriRCosta/gcpai.git
   cd gcpai
   ```

2. **Run the installation script:**

   ```bash
   ./install.sh
   ```

The script will automatically:

- Create a local Python virtual environment (`.venv`).
- Install all the required dependencies into it.
- Create the `gcpai` command in your system, making it available from any directory.

Follow any instructions provided by the script, such as adding `~/bin` to your PATH if it's not already configured.

## Configuration

After running the `install.sh` script, a `.env` file will be created in the project directory. You just need to open this file and add your OpenAI API key:

    OPENAI_API_KEY="your_secret_api_key_here"

## Usage

The main command is `gcpai`. You can use flags to customize its behavior.

### Examples

**1. Generate a commit message:**
Simply run the command. It's already add (`git add .`) when you run this command.

```bash
gcpai
```

2. Generate a branch name, then a commit message:
   Use the --branch (or -b) flag.

```bash
gcpai --branch
```

3. Full workflow: Branch, Commit, Push, and open PR:
   Combine the --branch and --pr flags for a complete automated workflow.

```bash
gcpai -b --pr
```

Interactive Prompts

The script will ask for your confirmation at various stages.

    Press Enter or y to accept a suggestion.
    Press r to regenerate a new suggestion.
    Press n to cancel an action.
