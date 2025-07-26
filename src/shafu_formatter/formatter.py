import re


def format_solidity(code):
    lines = code.split('\n')
    
    # Find variable declarations and group them into contiguous blocks
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
            # If we hit a non-declaration line and have declarations in current block, save the block
            if current_block:
                declaration_blocks.append(current_block)
                current_block = []
    
    # Don't forget the last block if file ends with declarations
    if current_block:
        declaration_blocks.append(current_block)
    
    # Process each block separately
    for block in declaration_blocks:
        if not block:
            continue
        
        # Find longest type in this block and align the visibility keyword
        max_length = max(len(d['type']) for d in block)
        target_width = max_length + 1  # longest type + 1 space
        
        for d in block:
            spaces_needed = target_width - len(d['type'])
            padding = ' ' * spaces_needed
            lines[d['index']] = f"{d['indent']}{d['type']}{padding}{d['visibility']}{d['rest']}"
    
    return '\n'.join(lines) 