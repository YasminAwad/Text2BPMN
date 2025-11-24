import os
import subprocess
import pathlib
import pytest

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_DIR = BASE_DIR / "assets" / "examples"
OUTPUT_DIR = BASE_DIR / "output"

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
    - Runs the CLI tool with each example input file
    - Saves BPMN + reasoning in the output preserving input subfolder structure
    """
    relative_path = input_file.relative_to(EXAMPLES_DIR)
    output_subfolder = OUTPUT_DIR / relative_path.parent
    output_subfolder.mkdir(parents=True, exist_ok=True)

    name = input_file.stem
    out_bpmn = output_subfolder / f"{name}.bpmn"
    out_reasoning = output_subfolder / f"{name}_reasoning.txt"

    cmd = [
    "text2bpmn",
    "--file",
    str(input_file),
    "--output",
    str(out_bpmn)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Assert CLI ran successfully
    assert result.returncode == 0, f"CLI failed for {input_file.name}"

    # Ensure output BPMN file was created
    assert out_bpmn.exists(), f"Missing BPMN output: {out_bpmn}"

    # Extract Reasoning from the CLI output and save it
    reasoning_text = extract_reasoning_from_output(result.stdout)
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
