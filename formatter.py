import re


def format_solidity(code):
    lines = code.split('\n')
    
    # Find variable declarations
    pattern = r'^(\s*)(uint\d*|address|bool|bytes\d*|string)(\s+)(public|private|internal|external)(.*)$'
    declarations = []
    
    for i, line in enumerate(lines):
        match = re.match(pattern, line)
        if match:
            declarations.append({
                'index': i,
                'indent': match.group(1),
                'type': match.group(2),
                'visibility': match.group(4),
                'rest': match.group(5)
            })
    
    if not declarations:
        return code
    
    # Find longest type and align the visibility keyword
    max_length = max(len(d['type']) for d in declarations)
    target_width = max_length + 1  # longest type + 1 space
    
    for d in declarations:
        spaces_needed = target_width - len(d['type'])
        padding = ' ' * spaces_needed
        lines[d['index']] = f"{d['indent']}{d['type']}{padding}{d['visibility']}{d['rest']}"
    
    return '\n'.join(lines) 