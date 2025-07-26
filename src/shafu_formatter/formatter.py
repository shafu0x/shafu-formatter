import subprocess
import tempfile
import os
import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class FormattingContext:
    """Context for tracking formatting state"""

    lines: List[str]
    source_code: str


class SolidityFormatter:
    """Simple regex-based Solidity formatter"""

    def __init__(self):
        self.context: Optional[FormattingContext] = None

    def format(self, source_code: str) -> str:
        """Main formatting entry point"""
        # First run forge fmt if available
        formatted_code = self._run_forge_fmt(source_code)

        # Initialize formatting context
        lines = formatted_code.split("\n")
        self.context = FormattingContext(lines=lines, source_code=formatted_code)

        # Apply formatting rules
        self._convert_uint256_to_uint()
        self._format_import_statements()
        self._format_variable_declarations()
        self._format_function_declarations()
        self._format_variable_assignments()

        # Preserve original trailing newline behavior
        result = "\n".join(self.context.lines)
        if not source_code.endswith("\n") and result.endswith("\n"):
            result = result.rstrip("\n")
        elif source_code.endswith("\n") and not result.endswith("\n"):
            result += "\n"

        return result

    def _run_forge_fmt(self, code: str) -> str:
        """Run forge fmt as a foundation"""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sol", delete=False
            ) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            result = subprocess.run(
                ["forge", "fmt", temp_file_path],
                capture_output=True,
                text=True,
                check=True,
            )

            with open(temp_file_path, "r") as temp_file:
                formatted_code = temp_file.read()

            os.unlink(temp_file_path)
            return formatted_code

        except subprocess.CalledProcessError as e:
            print(f"Warning: forge fmt failed: {e}")
        except FileNotFoundError:
            print("Warning: forge not found, skipping forge fmt")
        except Exception as e:
            print(f"Warning: Error running forge fmt: {e}")

        return code

    def _format_import_statements(self) -> None:
        """Format and align import statements"""
        # Find import statement lines using regex
        import_pattern = re.compile(r"^(\s*import\s+.+?)\s+from\s+(.+)$")
        import_lines = []

        for line_idx, line in enumerate(self.context.lines):
            if import_pattern.match(line):
                import_lines.append(line_idx)

        if len(import_lines) <= 1:
            return

        # Calculate max import part length
        max_import_length = 0
        for line_idx in import_lines:
            line = self.context.lines[line_idx]
            match = import_pattern.match(line)
            if match:
                import_part = match.group(1).strip()
                max_import_length = max(max_import_length, len(import_part))

        # Apply alignment
        for line_idx in import_lines:
            line = self.context.lines[line_idx]
            match = import_pattern.match(line)
            if match:
                import_part = match.group(1).strip()
                from_part = match.group(2).strip()
                indent = line[: len(line) - len(line.lstrip())]

                # Calculate padding
                padding_needed = max_import_length - len(import_part)
                padding = " " * (padding_needed + 1)  # +1 for separation

                # Reconstruct line
                self.context.lines[line_idx] = (
                    f"{indent}{import_part}{padding}from {from_part}"
                )

    def _format_variable_declarations(self) -> None:
        """Format and align variable declarations"""
        # Find variable declaration lines using regex
        var_pattern = re.compile(
            r"^\s*(uint\d*|address|bool|bytes\d*|string)\s+(public|private|internal)\s+"
        )
        var_lines = []

        for line_idx, line in enumerate(self.context.lines):
            if var_pattern.match(line) and not line.strip().startswith("//"):
                var_lines.append(line_idx)

        if len(var_lines) <= 1:
            return

        # Group consecutive variable declarations
        groups = []
        current_group = []

        for line_idx in var_lines:
            if not current_group or line_idx == current_group[-1] + 1:
                current_group.append(line_idx)
            else:
                if len(current_group) > 1:
                    groups.append(current_group)
                current_group = [line_idx]

        if len(current_group) > 1:
            groups.append(current_group)

        # Process each group
        for group in groups:
            if len(group) <= 1:
                continue

            # Calculate max type length in this group
            max_type_length = 0
            group_info = []

            for line_idx in group:
                line = self.context.lines[line_idx]
                match = var_pattern.match(line)
                if match:
                    type_name = match.group(1)
                    max_type_length = max(max_type_length, len(type_name))
                    group_info.append((line_idx, line, type_name))

            # Apply alignment
            for line_idx, original_line, type_name in group_info:
                # Calculate padding
                padding_needed = max_type_length - len(type_name)
                padding = " " * padding_needed

                # Replace the type with padded version
                self.context.lines[line_idx] = var_pattern.sub(
                    lambda m: f"{original_line[: m.start(1)]}{m.group(1)}{padding} {m.group(2)} ",
                    original_line,
                    count=1,
                )

    def _format_function_declarations(self) -> None:
        """Format function declarations with proper multiline style"""

        i = 0
        while i < len(self.context.lines):
            line = self.context.lines[i]

            # Pattern 1: Single-line function with visibility on same line
            single_line_pattern = re.compile(
                r"^(\s*function\s+\w+)\(([^)]*)\)\s*(.+?)\s*\{?\s*$"
            )
            match = single_line_pattern.match(line)
            if match and any(
                vis in match.group(3)
                for vis in ["external", "public", "private", "internal"]
            ):
                self._convert_function_to_multiline(i, match)
                i += 10  # Skip ahead since we added lines
                continue

            # Pattern 2: Function signature line (parameters on same line, visibility on next lines)
            func_sig_pattern = re.compile(r"^(\s*function\s+\w+)\(([^)]*)\)\s*$")
            match = func_sig_pattern.match(line)
            if match:
                # Look ahead to see if this needs parameter reformatting
                params_str = match.group(2).strip()
                params = (
                    [p.strip() for p in params_str.split(",") if p.strip()]
                    if params_str
                    else []
                )
                if len(params) > 2:
                    self._reformat_function_parameters(i, match)
                    i += len(params) + 2  # Skip the new lines we added
                    continue

            i += 1

    def _convert_function_to_multiline(self, line_idx: int, match) -> None:
        """Convert single-line function to proper multiline format"""
        func_name_part = match.group(1)  # "    function funcName"
        params_str = match.group(2).strip()  # parameter list
        after_params = match.group(
            3
        ).strip()  # everything after closing paren (visibility, modifiers, etc.)

        # Remove trailing '{' if present
        if after_params.endswith("{"):
            after_params = after_params[:-1].strip()

        indent = self.context.lines[line_idx][
            : len(self.context.lines[line_idx])
            - len(self.context.lines[line_idx].lstrip())
        ]

        new_lines = []

        # Handle parameters
        params = (
            [p.strip() for p in params_str.split(",") if p.strip()]
            if params_str
            else []
        )

        if len(params) > 2:
            # Multi-line parameter format
            new_lines.append(f"{func_name_part}(")
            for i, param in enumerate(params):
                if i == len(params) - 1:
                    new_lines.append(f"{indent}    {param}")
                else:
                    new_lines.append(f"{indent}    {param},")
            new_lines.append(f"{indent})")
        else:
            # Single line parameters
            new_lines.append(f"{func_name_part}({params_str})")

        # Handle visibility and modifiers
        if after_params:
            # Split visibility and modifiers
            parts = after_params.split()
            for part in parts:
                new_lines.append(f"{indent}    {part}")

        # Add opening brace
        new_lines.append(f"{indent}{{")

        # Replace the original line with multiple lines
        self.context.lines[line_idx : line_idx + 1] = new_lines

    def _reformat_function_parameters(self, line_idx: int, match) -> None:
        """Reformat function parameters to be on separate lines when >2 params"""
        func_name_part = match.group(1)  # "    function funcName"
        params_str = match.group(2).strip()  # parameter list

        params = [p.strip() for p in params_str.split(",") if p.strip()]
        indent = self.context.lines[line_idx][
            : len(self.context.lines[line_idx])
            - len(self.context.lines[line_idx].lstrip())
        ]

        new_lines = []
        new_lines.append(f"{func_name_part}(")

        for i, param in enumerate(params):
            if i == len(params) - 1:
                new_lines.append(f"{indent}    {param}")
            else:
                new_lines.append(f"{indent}    {param},")

        new_lines.append(f"{indent})")

        # Replace just the function signature line
        self.context.lines[line_idx : line_idx + 1] = new_lines

    def _format_variable_assignments(self) -> None:
        """Format variable assignments with aligned = operators"""
        assignment_groups = self._find_assignment_groups()

        for group in assignment_groups:
            if len(group) <= 1:
                continue

            max_var_length = max(len(parts[0]) for line_idx, parts in group)

            for line_idx, parts in group:
                var_part, value_part = parts
                padding_needed = max_var_length - len(var_part)
                padding = " " * padding_needed

                # Find the indent
                original_line = self.context.lines[line_idx]
                indent = original_line[
                    : len(original_line) - len(original_line.lstrip())
                ]

                self.context.lines[line_idx] = (
                    f"{indent}{var_part}{padding} = {value_part}"
                )

    def _find_assignment_groups(self) -> List[List]:
        """Find consecutive groups of assignment statements"""
        groups = []
        current_group = []

        for i, line in enumerate(self.context.lines):
            stripped = line.strip()

            # Check if line looks like an assignment
            if (
                "=" in stripped
                and not stripped.startswith("//")
                and "pragma" not in stripped
                and "import" not in stripped
            ):
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    var_part = parts[0].strip()
                    value_part = parts[1].strip()
                    # Skip if it looks like a comparison
                    if not any(op in var_part for op in ["==", "!=", "<=", ">="]):
                        current_group.append((i, (var_part, value_part)))
                        continue

            # End current group
            if current_group:
                groups.append(current_group)
                current_group = []

        if current_group:
            groups.append(current_group)

        return groups

    def _convert_uint256_to_uint(self) -> None:
        """Convert uint256 to uint for shorter syntax"""
        for i, line in enumerate(self.context.lines):
            if not line.strip().startswith("//"):
                self.context.lines[i] = line.replace("uint256", "uint")


def format_solidity(code: str) -> str:
    """Main entry point for formatting Solidity code"""
    formatter = SolidityFormatter()
    return formatter.format(code)
