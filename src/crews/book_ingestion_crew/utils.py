"""Utility functions for book ingestion crew."""
import re
from typing import Dict, Any, List


def parse_baron_filename(filename: str) -> Dict[str, Any]:
    """
    Parse baron-style filename to extract group and position.
    
    Examples:
    - baron001.png → group=1, position=1, page=1
    - baron001 1.png → group=1, position=2, page=2
    - baron001 24.png → group=1, position=25, page=25
    - baron002.png → group=2, position=1, page=26
    - baron002 24.png → group=2, position=25, page=50
    
    Formula: page_number = (group - 1) * 25 + position
    """
    # Remove file extension
    name_without_ext = filename.rsplit('.', 1)[0]
    
    # Pattern: baron(\d{3})(?:\s+(\d+))?
    # Matches: baron001 or baron001 24
    pattern = r'baron(\d{3})(?:\s+(\d+))?'
    match = re.match(pattern, name_without_ext, re.IGNORECASE)
    
    if not match:
        raise ValueError(f"Filename '{filename}' doesn't match baron pattern")
    
    group_str = match.group(1)
    position_str = match.group(2)
    
    # Convert group to int (e.g., "001" → 1)
    group = int(group_str)
    
    # Position: if no suffix, it's position 1
    # if suffix exists, position = suffix + 1
    if position_str is None:
        position = 1
    else:
        position = int(position_str) + 1
    
    # Calculate page number
    page_number = (group - 1) * 25 + position
    
    return {
        'filename': filename,
        'group': group,
        'position': position,
        'page_number': page_number,
        'group_str': group_str,
        'position_str': position_str or ''
    }


def sort_book_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort book files by their calculated page number.
    
    Expects files to have 'name' or 'file_name' field.
    Adds 'page_info' field with parsed information.
    """
    # Parse each filename and add page info
    for file in files:
        try:
            # Handle both 'name' and 'file_name' fields
            filename = file.get('file_name') or file.get('name')
            if not filename:
                raise ValueError("No filename found")
            
            page_info = parse_baron_filename(filename)
            file['page_info'] = page_info
            file['calculated_page_number'] = page_info['page_number']
            # Ensure we have both fields
            file['file_name'] = filename
            file['name'] = filename
        except ValueError as e:
            # If parsing fails, assign a high page number to sort it to the end
            file['page_info'] = None
            file['calculated_page_number'] = 9999
    
    # Sort by calculated page number
    sorted_files = sorted(files, key=lambda x: x['calculated_page_number'])
    
    return sorted_files


# Test the parser
if __name__ == "__main__":
    test_files = [
        "baron001.png",      # Should be page 1
        "baron001 1.png",    # Should be page 2
        "baron001 23.png",   # Should be page 24
        "baron001 24.png",   # Should be page 25
        "baron002.png",      # Should be page 26
        "baron002 1.png",    # Should be page 27
        "baron002 24.png",   # Should be page 50
    ]
    
    print("Testing filename parser:")
    print("-" * 50)
    
    for filename in test_files:
        try:
            info = parse_baron_filename(filename)
            print(f"{filename:20} → Page {info['page_number']:3d} (group {info['group']}, pos {info['position']})")
        except ValueError as e:
            print(f"{filename:20} → ERROR: {e}")