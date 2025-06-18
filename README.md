# Git AI Assistant

Este script utiliza a API da OpenAI para gerar mensagens de commit e nomes de branch com base nas suas alterações no Git.

## Pré-requisitos

- Python 3.8+
- Git

## Instalação

1. Clone o repositório:

   ```bash
   git clone [git@github.com:YuriRCosta/gcpai.git](git@github.com:YuriRCosta/gcpai.git)
   cd gcpai
   ```

2. (Opcional, mas recomendado) Crie e ative um ambiente virtual:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

## Configuração

1. Crie um arquivo `.env` na raiz do projeto.
2. Adicione sua chave da API da OpenAI a este arquivo:

   ```
   OPENAI_API_KEY="sua_chave_secreta_da_openai"
   ```

## Uso

Certifique-se de que seu script tenha permissão de execução:

```bash
chmod +x gcpai.py
```
