import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from solidity_parser import parse


@dataclass
class FormattingContext:
    """Context for tracking formatting state"""
    lines: List[str]
    source_code: str
    
    def get_line_for_position(self, start_pos: int, end_pos: int) -> int:
        """Get line number for a position in source code - simplified approach"""
        # Since we don't have exact position info, we'll use line-based matching
        return -1


class SolidityASTFormatter:
    """AST-based Solidity formatter using solidity-parser"""
    
    def __init__(self):
        self.context: Optional[FormattingContext] = None
    
    def format(self, source_code: str) -> str:
        """Main formatting entry point"""
        # First run forge fmt if available
        formatted_code = self._run_forge_fmt(source_code)
        
        # Parse the code into AST
        try:
            ast = parse(formatted_code)
        except Exception as e:
            print(f"Warning: AST parsing failed: {e}, using original code")
            return formatted_code
        
        # Initialize formatting context
        lines = formatted_code.split('\n')
        self.context = FormattingContext(lines=lines, source_code=formatted_code)
        
        # Convert uint256 to uint first (before alignment calculations)
        self._convert_uint256_to_uint()
        
        # Apply AST-based formatting rules
        self._format_import_statements(ast)
        self._format_variable_declarations(ast)
        self._format_function_declarations(ast)
        self._format_variable_assignments()
        
        # Preserve original trailing newline behavior
        result = '\n'.join(self.context.lines)
        if not source_code.endswith('\n') and result.endswith('\n'):
            result = result.rstrip('\n')
        elif source_code.endswith('\n') and not result.endswith('\n'):
            result += '\n'
        
        return result
    
    def _run_forge_fmt(self, code: str) -> str:
        """Run forge fmt as a foundation"""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sol", delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            result = subprocess.run(
                ["forge", "fmt", temp_file_path], 
                capture_output=True, 
                text=True, 
                check=True
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
    
    def _format_import_statements(self, ast: Dict) -> None:
        """Format and align import statements"""
        imports = []
        self._collect_imports(ast, imports)
        
        if len(imports) <= 1:
            return
        
        # Find import statement lines
        import_lines = []
        for line_idx, line in enumerate(self.context.lines):
            if line.strip().startswith('import') and ' from ' in line:
                import_lines.append(line_idx)
        
        if not import_lines:
            return
        
        # Calculate max import part length
        max_import_length = 0
        for line_idx in import_lines:
            line = self.context.lines[line_idx]
            import_start = line.find('import')
            from_pos = line.find(' from ')
            
            if import_start >= 0 and from_pos > import_start:
                import_part = line[import_start:from_pos].strip()
                max_import_length = max(max_import_length, len(import_part))
        
        # Apply alignment
        for line_idx in import_lines:
            line = self.context.lines[line_idx]
            import_start = line.find('import')
            from_pos = line.find(' from ')
            
            if import_start >= 0 and from_pos > import_start:
                import_part = line[import_start:from_pos].strip()
                from_part = line[from_pos:].strip()
                indent = line[:import_start]
                
                # Calculate padding
                padding_needed = max_import_length - len(import_part)
                padding = ' ' * (padding_needed + 1)  # +1 for separation
                
                # Reconstruct line
                self.context.lines[line_idx] = f"{indent}{import_part}{padding}{from_part}"
    
    def _collect_imports(self, node: Dict, imports: List) -> None:
        """Recursively collect import statements"""
        if isinstance(node, dict):
            if node.get('type') == 'ImportDirective':
                imports.append(node)
            
            # Recursively search children
            if 'children' in node:
                for child in node['children']:
                    self._collect_imports(child, imports)
            
            # Also search other dict values that might contain nodes
            for key, value in node.items():
                if key != 'children' and isinstance(value, (dict, list)):
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                self._collect_imports(item, imports)
                    else:
                        self._collect_imports(value, imports)
    
    def _format_variable_declarations(self, ast: Dict) -> None:
        """Format and align variable declarations"""
        state_vars = []
        self._collect_state_variables(ast, state_vars)
        
        if len(state_vars) <= 1:
            return
        
        # Find variable declaration lines
        var_lines = []
        for line_idx, line in enumerate(self.context.lines):
            stripped = line.strip()
            # Look for state variable patterns
            if any(visibility in stripped for visibility in ['public', 'private', 'internal', 'external']):
                if any(type_name in stripped for type_name in ['uint', 'address', 'bool', 'bytes', 'string']):
                    if not stripped.startswith('function') and not stripped.startswith('//'):
                        var_lines.append(line_idx)
        
        if not var_lines:
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
                stripped = line.strip()
                indent = line[:len(line) - len(stripped)]
                parts = stripped.split()
                
                if len(parts) >= 3:
                    type_name = parts[0]
                    max_type_length = max(max_type_length, len(type_name))
                    group_info.append((line_idx, indent, parts))
            
            # Apply alignment
            for line_idx, indent, parts in group_info:
                if len(parts) >= 3:
                    type_name = parts[0]
                    visibility = parts[1]
                    rest = ' '.join(parts[2:])
                    
                    # Calculate padding
                    padding_needed = max_type_length - len(type_name)
                    padding = ' ' * padding_needed
                    
                    # Reconstruct line
                    old_line = self.context.lines[line_idx]
                    new_line = f"{indent}{type_name}{padding} {visibility} {rest}"
                    self.context.lines[line_idx] = new_line
    
    def _collect_state_variables(self, node: Dict, state_vars: List) -> None:
        """Recursively collect state variable declarations"""
        if isinstance(node, dict):
            if node.get('type') == 'StateVariableDeclaration':
                state_vars.append(node)
            
            # Recursively search children
            if 'children' in node:
                for child in node['children']:
                    self._collect_state_variables(child, state_vars)
            
            # Also search other dict values that might contain nodes
            for key, value in node.items():
                if key != 'children' and isinstance(value, (dict, list)):
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                self._collect_state_variables(item, state_vars)
                    else:
                        self._collect_state_variables(value, state_vars)
    
    def _format_function_declarations(self, ast: Dict) -> None:
        """Format function declarations into multi-line style"""
        
        # Find function declaration lines and convert to multi-line
        for line_idx, line in enumerate(self.context.lines):
            stripped = line.strip()
            
            # Look for single-line function patterns
            if (stripped.startswith('function') and '(' in stripped and ')' in stripped and 
                (' external ' in stripped or ' public ' in stripped or ' private ' in stripped or ' internal ' in stripped) and
                stripped.endswith('{')):
                
                self._convert_function_to_multiline(line_idx)
    
    def _convert_function_to_multiline(self, line_idx: int) -> None:
        """Convert a single-line function declaration to multi-line format"""
        line = self.context.lines[line_idx]
        stripped = line.strip()
        indent = line[:len(line) - len(stripped)]
        
        # Remove trailing '{'
        if stripped.endswith('{'):
            stripped = stripped[:-1].strip()
        
        # Parse the function declaration
        # Pattern: function name(params) visibility [modifiers]
        
        # Find the function signature part (everything up to first visibility keyword)
        visibilities = ['external', 'public', 'private', 'internal']
        
        func_sig_end = -1
        visibility_start = -1
        
        for vis in visibilities:
            pos = stripped.find(' ' + vis + ' ')
            if pos >= 0:
                func_sig_end = pos
                visibility_start = pos + 1
                break
            # Also check if visibility is at the end
            if stripped.endswith(' ' + vis):
                func_sig_end = len(stripped) - len(vis) - 1
                visibility_start = len(stripped) - len(vis)
                break
        
        if func_sig_end == -1:
            # Couldn't parse, leave as is
            return
        
        func_signature = stripped[:func_sig_end].strip()
        remaining = stripped[visibility_start:].strip()
        
        # Split remaining into visibility and modifiers
        parts = remaining.split()
        if not parts:
            return
        
        visibility = parts[0]
        modifiers = parts[1:] if len(parts) > 1 else []
        
        # Build multi-line format
        new_lines = []
        new_lines.append(f"{indent}{func_signature}")
        new_lines.append(f"{indent}    {visibility}")
        
        # Add modifiers on separate lines
        for modifier in modifiers:
            new_lines.append(f"{indent}    {modifier}")
        
        new_lines.append(f"{indent}{{")
        
        # Replace the original line with multiple lines
        self.context.lines[line_idx:line_idx+1] = new_lines
    
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
                padding = ' ' * padding_needed
                
                # Find the indent
                original_line = self.context.lines[line_idx]
                indent = original_line[:len(original_line) - len(original_line.lstrip())]
                
                self.context.lines[line_idx] = f"{indent}{var_part}{padding} = {value_part}"
    
    def _find_assignment_groups(self) -> List[List]:
        """Find consecutive groups of assignment statements"""
        groups = []
        current_group = []
        
        for i, line in enumerate(self.context.lines):
            stripped = line.strip()
            
            # Check if line looks like an assignment
            if '=' in stripped and not stripped.startswith('//') and 'pragma' not in stripped and 'import' not in stripped:
                parts = stripped.split('=', 1)
                if len(parts) == 2:
                    var_part = parts[0].strip()
                    value_part = parts[1].strip()
                    # Skip if it looks like a comparison
                    if not any(op in var_part for op in ['==', '!=', '<=', '>=']):
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
            if not line.strip().startswith('//'):
                self.context.lines[i] = line.replace('uint256', 'uint')


def format_solidity(code: str) -> str:
    """Main entry point for formatting Solidity code"""
    formatter = SolidityASTFormatter()
    return formatter.format(code)
