# Code Review Rules

## TypeScript

- Use const/let, never var
- Prefer interfaces over types
- No any types

## React

- Use functional components
- Prefer named exports

## Python

### Imports

- Usar imports absolutos (`from app.xxx`) sobre relativos (`from ..xxx`)
- Orden: stdlib → third-party → local/app (ver flake8-import-order)
- No imports wildcard (`from x import *`)

### Nomenclatura

- Clases: PascalCase (`InvoiceService`)
- funciones/variables: snake_case (`get_rag_service`)
- Constantes: UPPER_SNAKE_CASE (`MAX_RETRIES`)
- Métodos privados: `_underscore_prefix`
- Archivos: snake_case (`rag_service.py`)

### Tipado

- Type hints obligatorios en funciones públicas
- Usar `X | None` en vez de `Optional[X]`
- Evitar `Any`

### Estructura

- Máximo 150-200 líneas por archivo
- Una clase pública por archivo
- Dependencias inyectadas en `__init__`, no en métodos
- Async/await: solo si hay I/O real (red, disco)

### Docstrings

- Clases públicas con docstring
- Funciones >10 líneas: documentar Args y Returns
- Usar Google style o NumPy style

### Testing

- Tests en `tests/` paralelo a `app/`
- Nombrar: `test_<module>_<function>.py`
- Un assert por test cuando sea posible
- Mockear I/O, no lógica de negocio

### Errores

- Exceptions custom en `domain/exceptions.py`
- Jerarquía: base exception → errores específicos
- No usar `except Exception` sin loguear
- Loguear antes de reraisear
