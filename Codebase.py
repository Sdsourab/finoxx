import os
from pathlib import Path

def generate_ai_context(output_filename="ai_master_context.txt"):
    # Get the absolute 100% accurate path of your project root
    base_dir = Path.cwd()
    
    # Configuration: What to include and what to ignore
    allowed_extensions = {'.py', '.html', '.css', '.js', '.json', '.md', '.sql'}
    ignore_dirs = {'.git', '__pycache__', 'venv', 'env', 'node_modules', '.streamlit', '.idea'}
    ignore_files = {output_filename, 'ai_packer.py', '.env'} # .env ignored for security
    
    print(f"Scanning Project Root: {base_dir}")
    
    with open(output_filename, 'w', encoding='utf-8', errors='replace') as out:
        # 1. WRITE METADATA AND ABSOLUTE ROOT PATH
        out.write(f"PROJECT ROOT DIRECTORY: {base_dir}\n")
        out.write("=" * 80 + "\n\n")
        
        # 2. GENERATE A VISUAL DIRECTORY TREE
        out.write("--- VISUAL DIRECTORY STRUCTURE ---\n")
        out.write("This helps the AI understand how folders are connected.\n\n")
        
        valid_files = [] # Store files to process later
        
        for path in sorted(base_dir.rglob('*')):
            # Skip ignored directories
            if any(part in ignore_dirs for part in path.parts):
                continue
            
            # Calculate folder depth for visual indentation
            depth = len(path.relative_to(base_dir).parts)
            indent = "    " * (depth - 1)
            
            if path.is_dir():
                out.write(f"{indent}📁 {path.name}/\n")
            elif path.is_file():
                if path.name not in ignore_files and path.suffix in allowed_extensions:
                    out.write(f"{indent}📄 {path.name}\n")
                    valid_files.append(path) # Save for the next step

        out.write("\n" + "=" * 80 + "\n")
        out.write("--- SOURCE CODE FILES ---\n")
        out.write("=" * 80 + "\n\n")

        # 3. WRITE THE ACTUAL CODE WITH 100% ACCURATE PATHS
        for file_path in valid_files:
            # Get the clean relative path (e.g., folder/subfolder/file.py)
            rel_path = file_path.relative_to(base_dir)
            
            # Distinct, highly visible separator for AI parsing
            out.write(f"\n{'/' * 80}\n")
            out.write(f"/// RELATIVE PATH : {rel_path}\n")
            out.write(f"/// ABSOLUTE PATH : {file_path}\n")
            out.write(f"{'/' * 80}\n\n")
            
            try:
                # errors='replace' guarantees it won't crash on bad characters
                content = file_path.read_text(encoding='utf-8', errors='replace')
                out.write(content)
                out.write("\n\n")
            except Exception as e:
                out.write(f"# [ ERROR: Could not read file contents: {e} ]\n\n")

    print(f"\n✅ Success! Advanced context file created at: {base_dir / output_filename}")

if __name__ == "__main__":
    generate_ai_context()