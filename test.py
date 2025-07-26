from pathlib import Path
from formatter import format_solidity


def test_all():
    before_dir = Path("tests/before")
    after_dir = Path("tests/after")
    
    passed = 0
    failed = 0
    
    for before_file in before_dir.glob("*"):
        if before_file.is_file():
            after_file = after_dir / before_file.name
            
            print(f"\nTesting {before_file.name}...")
            
            if not after_file.exists():
                print(f"❌ Missing {after_file}")
                failed += 1
                continue
            
            input_content = before_file.read_text()
            expected_content = after_file.read_text()
            result = format_solidity(input_content)
            
            if result.strip() == expected_content.strip():
                print("✅ PASSED")
                passed += 1
            else:
                print("❌ FAILED")
                print(f"Expected:\n{expected_content}")
                print(f"Got:\n{result}")
                failed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    test_all() 