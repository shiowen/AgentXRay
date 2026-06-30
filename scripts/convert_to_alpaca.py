import json
import os
import argparse

def format_files_to_string(output_data: dict) -> str:
    """
    Concatenates essential project files while preserving original formatting.
    - It respects all whitespace and newlines within the original content.
    - It adds a blank line between concatenated files for readability.
    """
    if not isinstance(output_data, dict):
        return ""

    content_parts = []
    file_categories_order = ["requirements", "code_files", "docs"]

    for category in file_categories_order:
        files_dict = output_data.get(category)
        if isinstance(files_dict, dict):
            for filename, content in sorted(files_dict.items()):
                if content and isinstance(content, str):
                    header = f"### file: {filename}"
                    full_block = f"{header}\n\n{content}"
                    content_parts.append(full_block)

    return "\n\n".join(content_parts)


def convert_dataset(source_path: str, target_path: str, instruction_key: str = 'input'):
    """
    Loads a dataset, converts it to Alpaca format preserving formatting,
    and saves it to the target path.
    """
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: source file not found: {source_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: failed to parse JSON source file: {source_path}")
        return

    alpaca_data = []
    for i, sample in enumerate(source_data):
        instruction = sample.get(instruction_key)
        if instruction is None:
            print(f"Warning: sample {i + 1} has no instruction key '{instruction_key}'; skipping.")
            continue

        output_val = sample.get('output', {})
        if isinstance(output_val, str):
            formatted_output = output_val
        else:
            formatted_output = format_files_to_string(output_val)

        alpaca_data.append({
            "instruction": instruction,
            "input": "",
            "output": formatted_output
        })

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(alpaca_data, f, ensure_ascii=False, indent=2)

    print("="*50)
    print("Dataset conversion completed with original formatting preserved.")
    print(f"Converted samples: {len(alpaca_data)}")
    print(f"Source file: {source_path}")
    print(f"Target file: {target_path}")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert project-format data to Alpaca SFT format."
    )
    parser.add_argument("--source", type=str, default="data/metagpt/test.json", help="Source JSON file")
    parser.add_argument("--target", type=str, default="data/metagpt/test_alpaca.json", help="Target Alpaca JSON file")
    parser.add_argument("--instruction_key", type=str, default="input", help="Source field used as instruction")

    args = parser.parse_args()
    convert_dataset(args.source, args.target, args.instruction_key)
