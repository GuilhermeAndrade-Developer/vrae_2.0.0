## Requisitos:

- Python 3.12.4
- pip 25.0.1

## Instalação:

1. Instalar Homebrew (se não estiver instalado):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Criar e ativar ambiente virtual:
```bash
# Criar ambiente virtual
python3 -m venv .venv

# Ativar ambiente virtual
source .venv/bin/activate

# Atualizar pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt
```

## Criar tabelas:
```bash
python3 init_database.py
```

## Iniciar Aplicação:

1. Iniciar Página WEB de TESTE:
```bash
python -m http.server 8080
```

2. Iniciar Servidor Principal:
```bash
hypercorn "vrae:app" --bind "0.0.0.0:5000" --reload --debug
```