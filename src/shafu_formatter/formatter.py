import re


def format_function_declarations(lines):
    new_lines = []
    function_pattern = r'^(\s*)(function\s+\w+\([^)]*\))\s+(public|private|internal|external)\s*\{(.*)$'
    
    for line in lines:
        match = re.match(function_pattern, line)
        if match:
            indent = match.group(1)
            function_sig = match.group(2)
            visibility = match.group(3)
            rest = match.group(4)
            
            new_lines.append(f"{indent}{function_sig} ")
            new_lines.append(f"{indent}    {visibility} ")
            new_lines.append(f"{indent}{{")
            if rest.strip():
                new_lines.append(f"{indent}    {rest}")
        else:
            new_lines.append(line)
    
    return new_lines


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


def format_solidity(code):
    lines = code.split('\n')
    
    # Format function declarations first
    lines = format_function_declarations(lines)
    
    # Then format variable declarations
    lines = format_variable_declarations(lines)
    
    return '\n'.join(lines) 