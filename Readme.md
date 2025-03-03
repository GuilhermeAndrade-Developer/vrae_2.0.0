## Requisitos:

- Python 3.12.4
- pip 25.0.1

## Instalação (Windows):

1. Criar e ativar ambiente virtual:
```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
.venv\Scripts\activate

# Atualizar pip
python -m pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt
```

## Criar tabelas:
```bash
python init_database.py
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