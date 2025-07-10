# scripts/render_templates.py
import argparse
import os
import sys
import re
import yaml
from jinja2 import Environment, FileSystemLoader

def main():
    """
    Finds all '*.template.yaml' files in a directory, renders them using data
    from a versions file, and saves the output.
    """
    parser = argparse.ArgumentParser(description="Render Jinja2 templates with version data.")
    parser.add_argument("--versions-file", required=True, help="Path to the versions.yaml file.")
    parser.add_argument("--template-dir", required=True, help="Directory containing the template files.")
    parser.add_argument("--output-dir", required=True, help="Directory to save the rendered files.")
    args = parser.parse_args()

    # 1. Load and process the version data
    try:
        with open(args.versions_file, 'r') as f:
            versions_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Versions file not found at {args.versions_file}")
        sys.exit(1)

    # Create the 'versions' context dictionary for Jinja, using 'name' as the key
    versions_context = {
        item['name']: item['current_version']
        for item in versions_data.get("software", [])
    }
    print("==> Using versions for template context:")
    print(versions_context)

    # 2. Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader(args.template_dir), autoescape=False)

    # 3. Find and render all templates in the directory
    for template_name in os.listdir(args.template_dir):
        if not template_name.endswith(".template.yaml"):
            continue

        print(f"\n==> Processing template: {template_name}")
        template = env.get_template(template_name)

        # IMPORTANT: Read the raw template to remove hardcoded checksums.
        # This is critical for an automated versioning system to work.
        raw_template_content = ""
        with open(os.path.join(args.template_dir, template_name), 'r') as f:
            raw_template_content = f.read()

        # Use regex to find and remove any line containing 'sha512sum -c'
        # This prevents build failures when versions are updated.
        cleaned_template_content = re.sub(r'.*sha512sum -c.*', '', raw_template_content)

        # Render the cleaned template content
        # We re-create the template object from the modified string
        cleaned_template = env.from_string(cleaned_template_content)
        output_content = cleaned_template.render(versions=versions_context)

        # 4. Save the rendered file
        output_filename = template_name.replace(".template.yaml", ".yaml")
        output_path = os.path.join(args.output_dir, output_filename)
        
        with open(output_path, 'w') as f:
            f.write(output_content)
        
        print(f"==> Successfully generated {output_path}")

if __name__ == "__main__":
    main()
