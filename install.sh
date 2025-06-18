#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMMAND_NAME="gcpai"
INSTALL_DIR="$HOME/bin"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo -e "${GREEN}Starting the installation of ${COMMAND_NAME}...${NC}"

if ! command -v python3 &>/dev/null; then
  echo -e "${YELLOW}ERROR: python3 is not installed. Please install it to continue.${NC}"
  exit 1
fi

echo -e "\nCreating Python virtual environment in '$VENV_DIR'..."
python3 -m venv "$VENV_DIR"

echo "Activating virtual environment to install dependencies..."
source "$VENV_DIR/bin/activate"

if [ -f "requirements.txt" ]; then
  echo "Installing Python dependencies from requirements.txt..."
  pip install -r requirements.txt
else
  echo -e "${YELLOW}WARNING: requirements.txt not found. Skipping dependency installation.${NC}"
fi

deactivate
echo "Virtual environment setup complete."

mkdir -p "$INSTALL_DIR"

echo "Creating wrapper script at '$INSTALL_DIR/$COMMAND_NAME'..."
WRAPPER_SCRIPT_PATH="$INSTALL_DIR/$COMMAND_NAME"

cat >"$WRAPPER_SCRIPT_PATH" <<EOF
#!/bin/bash
# Wrapper to run gcpai using its virtual environment
exec "$VENV_DIR/bin/python" "$PROJECT_DIR/gcpai.py" "\$@"
EOF

chmod +x "$WRAPPER_SCRIPT_PATH"

if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  echo -e "\n${YELLOW}WARNING: Your directory '$INSTALL_DIR' is not in your PATH.${NC}"
  echo "Please add '$INSTALL_DIR' to your PATH to use the '${COMMAND_NAME}' command."
  echo "You can do this by adding the following line to your shell config (e.g., ~/.bashrc, ~/.zshrc):"
  echo -e "\n  ${GREEN}export PATH=\"\$HOME/bin:\$PATH\"${NC}\n"
  echo "Then, restart your terminal."
fi

if [ ! -f .env ]; then
  echo -e "\nCreating configuration file '.env' from '.env.example'..."
  cp .env.example .env
  echo -e "${YELLOW}ACTION REQUIRED: Edit the '.env' file and insert your OpenAI API key.${NC}"
else
  echo -e "\n'.env' file already exists. No changes were made."
fi

echo -e "\n${GREEN}Installation completed successfully!${NC}"
echo "Please restart your terminal or source your shell config file for the '${COMMAND_NAME}' command to be recognized."
