# shafu Formatter

just run shafu bro

## Installation

### Using uv (recommended)

```bash
# Install the package
uv pip install -e .

# Or install with development dependencies
uv pip install -e ".[dev]"
```

### Using just commands

```bash
# Install normally
just install

# Install with development dependencies  
just install-dev
```

## Usage

### Command Line Interface

After installation, you can use the `shafu` command:

```bash
# Format a file and print output to console
shafu path/to/your/file.sol

# Format a file and write changes back to the file
shafu path/to/your/file.sol --write
```

### Running Directly

You can also run the formatter directly without installation:

```bash
# Format and print output
python src/shafu_formatter/main.py path/to/your/file.sol

# Format and write changes to file
python src/shafu_formatter/main.py path/to/your/file.sol --write

# Or using uv
uv run python src/shafu_formatter/main.py path/to/your/file.sol
```

## Examples

The `tests/` directory contains example Solidity files showing before and after formatting:

## Requirements

- forge
- Python 3.8 or higher
- tree-sitter-solidity >= 0.0.2
- tree-sitter >= 0.21.3

