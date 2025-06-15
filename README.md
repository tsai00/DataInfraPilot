# DataInfraPilot-BE


## Folder structure
```bash
├── backend <- Backend code (see ... for more details)
│   ├── src
│   │   ├── **/*.py
│   ├── Dockerfile
│   ├── pyproject.toml
├── demo <- Demo project (see ... for more details)
│   ├── src
│   │   ├── **/*.py
│   ├── Dockerfile
│   ├── pyproject.toml
├── frontend  <- Frontend code (see ... for more details)
│   ├── public
│   │   ├── *.png
│   ├── src
│   │   ├── **/*.tsx
│   ├── Dockerfile
├── pre-commit-config.yaml  <- pre-commit hooks setup
├── docker-compose.yaml  <- single Docker Compose for both BE and FE
├── README.md
└── .gitignore
```

## Local environment setup

1. Install uv:
`pip install uv`
2. Install project dependencies (will also install local project as a package):
`uv sync`
3. Install pre-commit
`pre-commit install`

## Linting
TBD

## Tests
TBD

## CI/CD
TBD