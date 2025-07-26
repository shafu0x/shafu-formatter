import subprocess
import tempfile
import os
import re
from typing import List, Tuple, Callable, Optional

# Precompiled regex patterns
IMPORT_PATTERN = re.compile(r"^(\s*import\s+.+?)\s+from\s+(.+)$")
VAR_PATTERN = re.compile(
    r"^\s*(uint\d*|address|bool|bytes\d*|string)\s+(public|private|internal)\s+"
)
SINGLE_LINE_FUNC_PATTERN = re.compile(
    r"^(\s*function\s+\w+)\(([^)]*)\)\s*(.+?)\s*\{?\s*$"
)
FUNC_SIG_PATTERN = re.compile(r"^(\s*function\s+\w+)\(([^)]*)\)\s*$")
CONSTRUCTOR_PATTERN = re.compile(r"^(\s*constructor)\(([^)]*)\)\s*(.*)$")


def run_forge_fmt(code: str) -> str:
    """Run forge fmt as a foundation, return original code on failure"""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sol", delete=False
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        subprocess.run(
            ["forge", "fmt", temp_file_path],
            capture_output=True,
            text=True,
            check=True,
        )

        with open(temp_file_path, "r") as temp_file:
            formatted_code = temp_file.read()

        os.unlink(temp_file_path)
        return formatted_code

    except (subprocess.CalledProcessError, FileNotFoundError, Exception):
        return code


def preserve_trailing_newline(original: str, formatted: str) -> str:
    """Preserve original trailing newline behavior"""
    if not original.endswith("\n") and formatted.endswith("\n"):
        return formatted.rstrip("\n")
    elif original.endswith("\n") and not formatted.endswith("\n"):
        return formatted + "\n"
    return formatted


def find_consecutive_matching_lines(
    lines: List[str],
    pattern: re.Pattern,
    filter_func: Optional[Callable[[str], bool]] = None,
) -> List[List[int]]:
    """Find groups of consecutive lines matching a pattern"""
    matching_lines = []
    for line_idx, line in enumerate(lines):
        if pattern.match(line) and (filter_func is None or filter_func(line)):
            matching_lines.append(line_idx)

    # Group consecutive lines
    groups = []
    current_group = []

    for line_idx in matching_lines:
        if not current_group or line_idx == current_group[-1] + 1:
            current_group.append(line_idx)
        else:
            if len(current_group) > 1:
                groups.append(current_group)
            current_group = [line_idx]

    if len(current_group) > 1:
        groups.append(current_group)

    return groups


def align_by_capture_groups(
    lines: List[str],
    pattern: re.Pattern,
    format_func: Callable[[str, re.Match, int], str],
    filter_func: Optional[Callable[[str], bool]] = None,
) -> List[str]:
    """Generic helper to align consecutive lines by capture groups"""
    result = lines.copy()
    groups = find_consecutive_matching_lines(lines, pattern, filter_func)

    for group in groups:
        if len(group) <= 1:
            continue

        # Calculate max length for alignment
        max_length = 0
        group_matches = []

        for line_idx in group:
            line = lines[line_idx]
            match = pattern.match(line)
            if match:
                group_matches.append((line_idx, match))
                # This will be overridden by specific format_func logic
                max_length = max(max_length, len(match.group(1)))

        # Apply formatting
        for line_idx, match in group_matches:
            result[line_idx] = format_func(lines[line_idx], match, max_length)

    return result


def convert_uint256_to_uint(lines: List[str]) -> List[str]:
    """Convert uint256 to uint for shorter syntax"""
    return [
        line.replace("uint256", "uint") if not line.strip().startswith("//") else line
        for line in lines
    ]


def format_import_statements(lines: List[str]) -> List[str]:
    """Format and align import statements"""

    def format_import(line: str, match: re.Match, max_length: int) -> str:
        import_part = match.group(1).strip()
        from_part = match.group(2).strip()
        indent = line[: len(line) - len(line.lstrip())]

        padding_needed = max_length - len(import_part)
        padding = " " * (padding_needed + 1)  # +1 for separation

        return f"{indent}{import_part}{padding}from {from_part}"

    return align_by_capture_groups(lines, IMPORT_PATTERN, format_import)


def format_variable_declarations(lines: List[str]) -> List[str]:
    """Format and align variable declarations"""

    def format_var(line: str, match: re.Match, max_length: int) -> str:
        type_name = match.group(1)
        padding_needed = max_length - len(type_name)
        padding = " " * padding_needed

        return VAR_PATTERN.sub(
            lambda m: f"{line[: m.start(1)]}{m.group(1)}{padding} {m.group(2)} ",
            line,
            count=1,
        )

    filter_func = lambda line: not line.strip().startswith("//")
    return align_by_capture_groups(lines, VAR_PATTERN, format_var, filter_func)


def format_function_declarations(lines: List[str]) -> List[str]:
    """Format function declarations with proper multiline style"""
    result = lines.copy()
    i = 0

    while i < len(result):
        line = result[i]

        # Pattern 1: Single-line function with visibility
        match = SINGLE_LINE_FUNC_PATTERN.match(line)
        if match and any(
            vis in match.group(3)
            for vis in ["external", "public", "private", "internal"]
        ):
            new_lines = convert_function_to_multiline(line, match)
            result[i : i + 1] = new_lines
            i += len(new_lines)
            continue

        # Pattern 2: Function signature with parameters on same line
        match = FUNC_SIG_PATTERN.match(line)
        if match:
            params_str = match.group(2).strip()
            params = (
                [p.strip() for p in params_str.split(",") if p.strip()]
                if params_str
                else []
            )
            if len(params) > 2:
                new_lines = reformat_function_parameters(line, match)
                result[i : i + 1] = new_lines
                i += len(new_lines)
                continue

        i += 1

    return result


def convert_function_to_multiline(line: str, match: re.Match) -> List[str]:
    """Convert single-line function to proper multiline format"""
    func_name_part = match.group(1)
    params_str = match.group(2).strip()
    after_params = match.group(3).strip()

    if after_params.endswith("{"):
        after_params = after_params[:-1].strip()

    indent = line[: len(line) - len(line.lstrip())]
    new_lines = []

    params = (
        [p.strip() for p in params_str.split(",") if p.strip()] if params_str else []
    )

    if len(params) > 2:
        new_lines.append(f"{func_name_part}(")
        for i, param in enumerate(params):
            if i == len(params) - 1:
                new_lines.append(f"{indent}    {param}")
            else:
                new_lines.append(f"{indent}    {param},")
        new_lines.append(f"{indent})")
    else:
        new_lines.append(f"{func_name_part}({params_str})")

    if after_params:
        parts = after_params.split()
        for part in parts:
            new_lines.append(f"{indent}    {part}")

    new_lines.append(f"{indent}{{")
    return new_lines


def reformat_function_parameters(line: str, match: re.Match) -> List[str]:
    """Reformat function parameters to be on separate lines when >2 params"""
    func_name_part = match.group(1)
    params_str = match.group(2).strip()

    params = [p.strip() for p in params_str.split(",") if p.strip()]
    indent = line[: len(line) - len(line.lstrip())]

    new_lines = [f"{func_name_part}("]

    for i, param in enumerate(params):
        if i == len(params) - 1:
            new_lines.append(f"{indent}    {param}")
        else:
            new_lines.append(f"{indent}    {param},")

    new_lines.append(f"{indent})")
    return new_lines


def format_constructors(lines: List[str]) -> List[str]:
    """Format constructor declarations with aligned parameters"""
    result = lines.copy()
    i = 0

    while i < len(result):
        line = result[i]

        # Check if this is a constructor line
        if "constructor(" in line and not line.strip().startswith("//"):
            # Find the constructor declaration and its parameters
            constructor_start = i
            constructor_lines = []

            # Collect all lines of the constructor declaration
            j = i
            while j < len(result):
                constructor_lines.append(result[j])
                # Check if this line ends the parameter list
                if ")" in result[j]:
                    break
                j += 1

            # Only process if we have multiple parameter lines
            if len(constructor_lines) > 2:  # constructor( + params + )
                # Parse the last line to separate ) and {
                last_line = constructor_lines[-1]
                last_line_stripped = last_line.strip()
                indent = constructor_lines[0][
                    : len(constructor_lines[0]) - len(constructor_lines[0].lstrip())
                ]

                # Check if ) and { are on the same line
                extra_after_paren = ""
                if ") {" in last_line_stripped:
                    extra_after_paren = " {"
                elif ")" in last_line_stripped and "{" in last_line_stripped:
                    # Find what comes after )
                    paren_idx = last_line_stripped.index(")")
                    extra_after_paren = last_line_stripped[paren_idx + 1 :].rstrip()

                # Extract parameters
                params = []
                for line_idx in range(1, len(constructor_lines) - 1):
                    param_line = constructor_lines[line_idx].strip()
                    if param_line.endswith(","):
                        param_line = param_line[:-1]
                    params.append(param_line)

                # Add the last parameter if it's before the closing )
                if len(constructor_lines) > 1:
                    last_param_line = constructor_lines[-1].strip()
                    if ")" in last_param_line:
                        # Extract parameter before )
                        param_part = last_param_line[
                            : last_param_line.index(")")
                        ].strip()
                        if param_part and param_part != "":
                            if param_part.endswith(","):
                                param_part = param_part[:-1]
                            params.append(param_part)

                # Find max lengths for three-column alignment
                max_type_length = 0
                max_modifier_length = 0
                param_parts = []

                for param in params:
                    if not param:  # Skip empty params
                        continue
                    # Split parameter into type and name parts
                    parts = param.split()
                    if len(parts) >= 2:
                        # Handle array types like "address[] memory"
                        if (
                            "memory" in parts
                            or "storage" in parts
                            or "calldata" in parts
                        ):
                            type_part = " ".join(parts[:-2])
                            memory_part = parts[-2]
                            name_part = parts[-1]
                            param_parts.append((type_part, memory_part, name_part))
                            max_type_length = max(max_type_length, len(type_part))
                            max_modifier_length = max(
                                max_modifier_length, len(memory_part)
                            )
                        else:
                            type_part = parts[0]
                            # Handle uint256 -> uint conversion
                            if type_part == "uint256":
                                type_part = "uint"
                            name_part = " ".join(parts[1:])
                            param_parts.append((type_part, None, name_part))
                            max_type_length = max(max_type_length, len(type_part))

                # Rebuild constructor with aligned parameters
                new_lines = [constructor_lines[0]]

                for idx, (type_part, memory_part, name_part) in enumerate(param_parts):
                    if memory_part:
                        # For params with memory/storage/calldata
                        type_padding = " " * (max_type_length - len(type_part) + 1)
                        modifier_padding = " " * (
                            max_modifier_length - len(memory_part) + 1
                        )
                        aligned_param = f"{type_part}{type_padding}{memory_part}{modifier_padding}{name_part}"
                    else:
                        # For simple type params - they need extra padding to account for missing modifier
                        type_padding = " " * (
                            max_type_length - len(type_part) + max_modifier_length + 2
                        )
                        aligned_param = f"{type_part}{type_padding}{name_part}"

                    if idx < len(param_parts) - 1:
                        new_lines.append(f"{indent}    {aligned_param},")
                    else:
                        new_lines.append(f"{indent}    {aligned_param}")

                # Add closing parenthesis with double space before {
                if extra_after_paren == " {":
                    extra_after_paren = "  {"
                new_lines.append(f"{indent}){extra_after_paren}")

                # Replace the old lines with new ones
                result[
                    constructor_start : constructor_start + len(constructor_lines)
                ] = new_lines
                i = constructor_start + len(new_lines)
                continue

        i += 1

    return result


def format_require_statements(lines: List[str]) -> List[str]:
    """Format require statements with aligned conditions and error messages"""
    result = lines.copy()

    # Find groups of consecutive require statements
    require_groups = []
    current_group = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("require(") and not line.strip().startswith("//"):
            current_group.append(i)
        else:
            if len(current_group) > 1:
                require_groups.append(current_group)
            current_group = []

    if len(current_group) > 1:
        require_groups.append(current_group)

    # Process each group
    for group in require_groups:
        # Parse require statements
        require_data = []
        max_left_length = 0
        max_operator_length = 0
        max_right_length = 0
        has_operators = False

        for line_idx in group:
            line = lines[line_idx]
            indent = line[: len(line) - len(line.lstrip())]
            stripped = line.strip()

            # Extract condition and error from require statement
            if "require(" in stripped and "," in stripped:
                # Find the matching parenthesis
                paren_count = 0
                condition_end = -1
                for i, char in enumerate(stripped):
                    if char == "(":
                        paren_count += 1
                    elif char == ")":
                        paren_count -= 1
                        if paren_count == 0:
                            condition_end = i
                            break

                if condition_end > 0:
                    # Extract the full require content
                    require_content = stripped[8:condition_end]  # Skip "require("

                    # Find the last comma that separates condition from error
                    comma_positions = []
                    paren_depth = 0
                    for i, char in enumerate(require_content):
                        if char == "(":
                            paren_depth += 1
                        elif char == ")":
                            paren_depth -= 1
                        elif char == "," and paren_depth == 0:
                            comma_positions.append(i)

                    if comma_positions:
                        last_comma = comma_positions[-1]
                        condition = require_content[:last_comma].strip()
                        error_part = require_content[last_comma + 1 :].strip()

                        # Parse the condition to find operators
                        # Common operators in order of precedence (longest first to avoid splitting <=)
                        operators = ["<=", ">=", "==", "!=", "<", ">", "&&", "||"]
                        operator_found = None
                        operator_pos = -1

                        for op in operators:
                            if op in condition:
                                # Find the operator position (not inside parentheses)
                                paren_depth = 0
                                for i in range(len(condition) - len(op) + 1):
                                    substring = condition[i : i + len(op)]
                                    # Check paren depth at this position
                                    for j in range(i):
                                        if condition[j] == "(":
                                            paren_depth += 1
                                        elif condition[j] == ")":
                                            paren_depth -= 1

                                    if substring == op and paren_depth == 0:
                                        operator_found = op
                                        operator_pos = i
                                        break

                                if operator_found:
                                    break

                        if operator_found and operator_pos >= 0:
                            left_part = condition[:operator_pos].strip()
                            right_part = condition[
                                operator_pos + len(operator_found) :
                            ].strip()

                            require_data.append(
                                (
                                    line_idx,
                                    indent,
                                    left_part,
                                    operator_found,
                                    right_part,
                                    error_part,
                                )
                            )
                            max_left_length = max(max_left_length, len(left_part))
                            max_operator_length = max(
                                max_operator_length, len(operator_found)
                            )
                            max_right_length = max(max_right_length, len(right_part))
                            has_operators = True
                        else:
                            # No operator found, treat as simple condition
                            require_data.append(
                                (line_idx, indent, condition, "", "", error_part)
                            )
                            # For lines without operators, we still need to account for left side alignment
                            if has_operators or any(
                                len(d) == 6 and d[3]
                                for d in require_data
                                if len(d) == 6
                            ):
                                max_left_length = max(max_left_length, len(condition))

        # Calculate the maximum condition length to determine error alignment
        max_condition_length = 0
        conditions_list = []

        for data in require_data:
            if len(data) == 6:  # Has data
                line_idx, indent, left, op, right, error = data

                # Align left side for all lines
                left_padding = " " * (max_left_length - len(left))

                # Build condition string
                if op:
                    op_padding = " " * (max_operator_length - len(op))
                    condition_str = f"{left}{left_padding} {op}{op_padding} {right}"
                else:
                    # For lines without operators, we need to leave space as if there was an operator
                    condition_str = left

                conditions_list.append((line_idx, indent, condition_str, error, op))
                if op:  # Only count lines with operators for max length
                    max_condition_length = max(max_condition_length, len(condition_str))

        # Rebuild require statements with proper error alignment
        for line_idx, indent, condition_str, error, op in conditions_list:
            if op:
                # Lines with operators - normal padding
                padding_after_comma = " " * (max_condition_length - len(condition_str))
                aligned_require = (
                    f"{indent}require({condition_str},{padding_after_comma} {error});"
                )
            else:
                # Lines without operators - special handling
                # Calculate padding to align with the longest condition
                padding_after_condition = " " * (
                    max_condition_length - len(condition_str)
                )
                aligned_require = f"{indent}require({condition_str},{padding_after_condition} {error});"

            result[line_idx] = aligned_require

    return result


def format_variable_assignments(lines: List[str]) -> List[str]:
    """Format variable assignments with aligned = operators"""
    assignment_groups = find_assignment_groups(lines)
    result = lines.copy()

    for group in assignment_groups:
        if len(group) <= 1:
            continue

        max_var_length = max(len(parts[0]) for line_idx, parts in group)

        for line_idx, parts in group:
            var_part, value_part = parts
            padding_needed = max_var_length - len(var_part)
            padding = " " * padding_needed

            original_line = lines[line_idx]
            indent = original_line[: len(original_line) - len(original_line.lstrip())]

            result[line_idx] = f"{indent}{var_part}{padding} = {value_part}"

    return result


def find_assignment_groups(lines: List[str]) -> List[List[Tuple[int, Tuple[str, str]]]]:
    """Find consecutive groups of assignment statements"""
    groups = []
    current_group = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if (
            "=" in stripped
            and not stripped.startswith("//")
            and "pragma" not in stripped
            and "import" not in stripped
            and "require(" not in stripped
        ):
            parts = stripped.split("=", 1)
            if len(parts) == 2:
                var_part = parts[0].strip()
                value_part = parts[1].strip()
                if not any(op in var_part for op in ["==", "!=", "<=", ">="]):
                    current_group.append((i, (var_part, value_part)))
                    continue

        if current_group:
            groups.append(current_group)
            current_group = []

    if current_group:
        groups.append(current_group)

    return groups


def add_double_space_before_brace(lines: List[str]) -> List[str]:
    """Add double space before opening brace in function/constructor declarations"""
    result = []
    for line in lines:
        # Match lines that end with ) { and add extra space
        if line.strip().endswith(") {"):
            result.append(line[:-2] + "  {")
        else:
            result.append(line)
    return result


def format_solidity(code: str) -> str:
    """Main entry point for formatting Solidity code"""
    # Run forge fmt first
    formatted_code = run_forge_fmt(code)

    # Convert to lines for processing
    lines = formatted_code.split("\n")

    # Apply formatting pipeline
    transformations = [
        convert_uint256_to_uint,
        format_import_statements,
        format_variable_declarations,
        format_function_declarations,
        format_constructors,
        format_require_statements,
        format_variable_assignments,
        add_double_space_before_brace,
    ]

    for transform in transformations:
        lines = transform(lines)

    # Convert back to string and preserve trailing newlines
    result = "\n".join(lines)
    return preserve_trailing_newline(code, result)
