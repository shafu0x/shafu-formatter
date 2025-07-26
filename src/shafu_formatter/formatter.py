import re
import subprocess
import tempfile
import os


def format_function_declarations(lines):
    new_lines = []
    # Updated pattern to capture any modifiers after visibility
    function_pattern = r'^(\s*)(function\s+\w+\([^)]*\))\s+(public|private|internal|external)(\s+\w+)*\s*\{(.*)$'
    
    for line in lines:
        match = re.match(function_pattern, line)
        if match:
            indent = match.group(1)
            function_sig = match.group(2)
            visibility = match.group(3)
            modifiers = match.group(4)  # This will capture any additional modifiers
            rest = match.group(5)
            
            new_lines.append(f"{indent}{function_sig}")
            new_lines.append(f"{indent}    {visibility}")
            
            # Add any additional modifiers on separate lines
            if modifiers:
                modifier_list = modifiers.strip().split()
                for modifier in modifier_list:
                    new_lines.append(f"{indent}    {modifier}")
            
            new_lines.append(f"{indent}{{")
            if rest.strip():
                new_lines.append(f"{indent}    {rest}")
        else:
            new_lines.append(line)
    
    return new_lines


def format_variable_assignments(lines):
    # Pattern to match variable assignments with = operator
    assignment_pattern = r'^(\s*)(\w+\s+\w+)\s*=\s*(.+)$'
    
    # Find all assignment lines and their positions
    assignments = []
    for i, line in enumerate(lines):
        match = re.match(assignment_pattern, line)
        if match:
            indent = match.group(1)
            variable_declaration = match.group(2)
            value = match.group(3)
            assignments.append({
                'index': i,
                'indent': indent,
                'variable_declaration': variable_declaration,
                'value': value
            })
    
    # Find the longest variable declaration in this block
    if assignments:
        max_length = max(len(assignment['variable_declaration']) for assignment in assignments)
        
        # Format each assignment with aligned = operators
        for assignment in assignments:
            spaces_needed = max_length - len(assignment['variable_declaration'])
            padding = ' ' * spaces_needed
            lines[assignment['index']] = f"{assignment['indent']}{assignment['variable_declaration']}{padding} = {assignment['value']}"
    
    return lines


def find_variable_declaration_blocks(lines):
    pattern = r'^(\s*)(uint\d*|address|bool|bytes\d*|string)(\s+)(public|private|internal|external)(.*)$'
    declaration_blocks = []
    current_block = []
    
    for i, line in enumerate(lines):
        match = re.match(pattern, line)
        if match:
            declaration = {
                'index': i,
                'indent': match.group(1),
                'type': match.group(2),
                'visibility': match.group(4),
                'rest': match.group(5)
            }
            current_block.append(declaration)
        else:
            if current_block:
                declaration_blocks.append(current_block)
                current_block = []
    
    # Don't forget the last block if file ends with declarations
    if current_block:
        declaration_blocks.append(current_block)
    
    return declaration_blocks


def format_variable_declaration_block(lines, block):
    if not block:
        return
    
    # Find longest type in this block and align the visibility keyword
    max_length = max(len(d['type']) for d in block)
    target_width = max_length + 1  # longest type + 1 space
    
    for d in block:
        spaces_needed = target_width - len(d['type'])
        padding = ' ' * spaces_needed
        lines[d['index']] = f"{d['indent']}{d['type']}{padding}{d['visibility']}{d['rest']}"


def format_variable_declarations(lines):
    declaration_blocks = find_variable_declaration_blocks(lines)
    
    # Process each block separately
    for block in declaration_blocks:
        format_variable_declaration_block(lines, block)
    
    return lines


def format_operator_spacing(lines):
    """Add consistent spacing around operators in expressions."""
    operators = ['+', '-', '*', '/', '=', '==', '!=', '<=', '>=', '<', '>', '&&', '||']
    
    for i, line in enumerate(lines):
        # Skip lines that are just whitespace or comments
        if not line.strip() or line.strip().startswith('//'):
            continue
            
        # Skip pragma and import lines
        if line.strip().startswith('pragma') or line.strip().startswith('import'):
            continue
            
        # Skip contract and function declaration lines
        if re.match(r'^\s*(contract|function|modifier|event|struct|enum|interface)', line.strip()):
            continue
            
        # Process the line to add spaces around operators
        processed_line = line
        
        # Handle operators in order of length (longer ones first to avoid conflicts)
        for op in sorted(operators, key=len, reverse=True):
            # Use word boundaries to avoid matching operators within identifiers
            if len(op) == 1:
                # Single character operators
                pattern = r'([^\s' + re.escape(op) + r'])' + re.escape(op) + r'([^\s' + re.escape(op) + r'])'
                replacement = r'\1 ' + op + r' \2'
            else:
                # Multi-character operators
                pattern = r'([^\s])' + re.escape(op) + r'([^\s])'
                replacement = r'\1 ' + op + r' \2'
            
            processed_line = re.sub(pattern, replacement, processed_line)
        
        lines[i] = processed_line
    
    return lines


def convert_uint256_to_uint(lines):
    """Convert uint256 back to uint for shorter syntax."""
    for i, line in enumerate(lines):
        # Replace uint256 with uint, but be careful not to replace in comments
        # Only replace if it's not in a comment line
        if not line.strip().startswith('//'):
            lines[i] = re.sub(r'\buint256\b', 'uint', line)
    return lines

def format_solidity(code):
    # First, run forge fmt on the code
    try:
        # Create a temporary file with .sol extension
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        # Run forge fmt on the temporary file
        result = subprocess.run(['forge', 'fmt', temp_file_path], 
                              capture_output=True, text=True, check=True)
        
        # Read the formatted code back
        with open(temp_file_path, 'r') as temp_file:
            formatted_code = temp_file.read()
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        # Use the forge-formatted code as input
        code = formatted_code
        
    except subprocess.CalledProcessError as e:
        # If forge fmt fails, continue with original code
        print(f"Warning: forge fmt failed: {e}")
    except FileNotFoundError:
        # If forge is not installed, continue with original code
        print("Warning: forge not found, skipping forge fmt")
    except Exception as e:
        # For any other errors, continue with original code
        print(f"Warning: Error running forge fmt: {e}")
    
    lines = code.split('\n')
    
    # Convert uint256 back to uint for shorter syntax
    lines = convert_uint256_to_uint(lines)
    
    # Format function declarations first
    lines = format_function_declarations(lines)
    
    # Then format variable declarations
    lines = format_variable_declarations(lines)
    
    # Finally format variable assignments
    lines = format_variable_assignments(lines)
    
    # Add operator spacing
    lines = format_operator_spacing(lines)
    
    return '\n'.join(lines) 