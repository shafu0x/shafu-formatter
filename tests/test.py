from pathlib import Path
import sys
import os

# Add the project root to the path so we can import from src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.shafu_formatter.formatter import format_solidity


def test_all():
    # Determine the correct paths based on current working directory
    test_dir = Path(__file__).parent
    before_dir = test_dir / "0_before"
    after_dir = test_dir / "1_after"

    passed = 0
    failed = 0

    for before_file in sorted(before_dir.glob("*")):
        if before_file.is_file():
            after_file = after_dir / before_file.name

            if not after_file.exists():
                print(f"❌ Missing {after_file}")
                failed += 1
                continue

            input_content = before_file.read_text()
            expected_content = after_file.read_text()
            result = format_solidity(input_content)

            if result.strip() == expected_content.strip():
                print(f"✅ {before_file.name}")
                passed += 1
            else:
                print(f"❌ {before_file.name} - FAILED")
                print(f"Expected:\n{expected_content}")
                print(f"Got:\n{result}")
                failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    test_all()
