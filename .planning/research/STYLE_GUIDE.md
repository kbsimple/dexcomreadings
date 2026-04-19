# Google Python Style Guide Research

**Analysis Date:** 2026-04-19

## Key Requirements for Compliance

### Docstrings

**Module Docstrings:**
- Start file with docstring describing contents and usage
- Use `"""` format (PEP 257)
- One-line summary max 80 chars, terminated by punctuation
- Include license boilerplate

**Function/Method Docstrings:**
- Mandatory for: public API, nontrivial size, non-obvious logic
- Include `Args:`, `Returns:`/`Yields:`, `Raises:` sections
- Should enable calling function without reading code

**Class Docstrings:**
- Required below class definition
- Document public attributes in `Attributes` section

**Test Modules:**
- Module-level docstrings not required

### Type Hints

**Requirements:**
- Annotate public APIs at minimum
- Use `X | None` for optional types (not `Optional`)
- Don't annotate `self` or `cls`
- Don't annotate `__init__` return value
- Prefer abstract types (`Sequence`) over concrete (`list`)

**Imports:**
- Can import multiple symbols from `typing`/`collections.abc` on one line
- Use `str` for text, `bytes` for binary (not `Text`)

### Main Function

- Main functionality in `main()` function
- Always check `if __name__ == '__main__'`
- Avoid top-level code execution

### Naming Conventions

| Type | Style |
|------|-------|
| Packages | `lower_with_under` |
| Modules | `lower_with_under` |
| Classes | `CapWords` |
| Exceptions | `CapWords` |
| Functions/Methods | `lower_with_under()` |
| Constants | `CAPS_WITH_UNDER` |
| Variables | `lower_with_under` |

**Avoid:**
- Single character names (except `i`, `j`, `k`, `e`, `f`)
- Dashes in module names
- Double underscore names
- Type names in variable names

### Imports

- Separate lines for imports (except `typing`/`collections.abc`)
- Order: `__future__`, stdlib, third-party, local
- Sort lexicographically within groups
- Use full package names (no relative imports)

### Other Mandatory Rules

**Line Length:**
- Maximum 80 characters
- No backslash continuation

**Indentation:**
- 4 spaces (never tabs)

**Semicolons:**
- No semicolons for multiple statements

**Strings:**
- Use `"""` for multi-line strings
- Avoid `+`/`+=` in loops for string accumulation

**Linting:**
- Run `pylint` on code
- Suppress with `# pylint: disable=...`

**Global State:**
- Avoid mutable global state
- Constants in ALL_CAPS_WITH_UNDERSCORE

**Exceptions:**
- Never use catch-all `except:` or `except Exception`
- Don't use `assert` for conditionals

---
*Research: 2026-04-19*