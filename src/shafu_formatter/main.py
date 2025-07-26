import sys
from pathlib import Path
from .formatter import format_solidity


def main():
    if len(sys.argv) < 2:
        print("Usage: shafu <file.sol> [--write]")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    write_mode = '--write' in sys.argv
    
    if not file_path.exists():
        print(f"Error: {file_path} not found")
        sys.exit(1)
    
    content = file_path.read_text()
    formatted = format_solidity(content)
    
    if write_mode:
        file_path.write_text(formatted)
        print(f"Formatted {file_path}")
    else:
        print(formatted)


if __name__ == "__main__":
    main() 