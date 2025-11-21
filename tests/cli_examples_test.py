import os
import subprocess
import pathlib
import pytest

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_DIR = BASE_DIR / "examples_inputs"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure output folder exists
OUTPUT_DIR.mkdir(exist_ok=True)


def get_all_input_files():
    """
    Finds all .txt and .md files inside examples_inputs/** folders.
    """
    files = []
    for folder in EXAMPLES_DIR.iterdir():
        if folder.is_dir():
            for f in folder.glob("**/*"):
                if f.suffix.lower() in {".txt", ".md"}:
                    files.append(f)
    return files


@pytest.mark.parametrize("input_file", get_all_input_files())
def test_generate_bpmn_from_examples(input_file):
    """
    Integration test:
    - Runs the CLI tool with each example input file
    - Saves BPMN + reasoning in the output/ folder
    """

    # Name of generated files
    name = input_file.stem
    out_bpmn = OUTPUT_DIR / f"{name}.bpmn"
    out_reasoning = OUTPUT_DIR / f"{name}_reasoning.txt"

    # CLI command
    cmd = [
    "text2bpmn",  # <-- the console script from setup.py
    "--file",
    str(input_file),
    "--output",
    str(out_bpmn)
    ]



    # Run CLI
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Print stdout/stderr for debugging if needed
    print(result.stdout)
    print(result.stderr)

    # Assert CLI ran successfully
    assert result.returncode == 0, f"CLI failed for {input_file.name}"

    # Ensure output BPMN file was created
    assert out_bpmn.exists(), f"Missing BPMN output: {out_bpmn}"

    # Extract Reasoning from the CLI output and save it
    # The CLI prints reasoning after "📜 Reasoning Report:"
    reasoning_text = extract_reasoning_from_output(result.stdout)
    print("Reasoning:")
    print(reasoning_text)

    out_reasoning.write_text(reasoning_text, encoding="utf-8")

    assert out_reasoning.exists(), f"Missing reasoning file: {out_reasoning}"


def extract_reasoning_from_output(output: str) -> str:
    """
    Extract reasoning from CLI output.
    
    Looks for "📜 Reasoning Report:" section in the output.
    """
    lines = output.split('\n')
    reasoning_lines = []
    capture = False
    
    for line in lines:
        if '📜 Reasoning Report:' in line:
            capture = True
            continue
        
        if capture:
            # Stop at the next section or end
            if line.startswith('===') or line.startswith('➡️'):
                break
            reasoning_lines.append(line)
    
    return '\n'.join(reasoning_lines).strip()
