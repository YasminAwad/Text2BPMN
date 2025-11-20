"""
CLI interface module for BPMN Generator using Click.
Handles command-line interface and console output formatting.
"""

import sys
import click
from typing import Optional

from .config import validate_api_key, get_model_config
from .utils.file_handler import read_process_description
from .core.llm import LLMService
from .core.generator import BPMNGeneratorService
from .core.validator import BPMNGenerationError


def display_header(process_description: str) -> None:
    click.echo("=" * 70)
    click.echo(click.style("💡Text2BPMN", fg="white", bold=True).center(80))
    click.echo("=" * 70)
    click.echo(f"\n📝 Process Description:")
    click.echo(f"{process_description}\n")
    click.echo("-" * 70)


def display_footer(output_path: str) -> None:
    click.echo(f"\n✅ BPMN diagram saved to: {click.style(output_path, fg='white', bold=True)}")
    click.echo("\n" + "=" * 70)
    click.echo(click.style("✨ Conversion complete!", fg="white", bold=True).center(70))
    click.echo("=" * 70)

    url = "http://demo.bpmn.io/"
    link = f"\033]8;;{url}\033\\bpmn.io\033]8;;\033\\"
    click.echo(f"\n➡️  You can drag and drop the .bpmn file at {link} for visualization")


def print_error(message: str) -> None:
    click.echo(click.style(f"\n❌ Error: {message}", fg="red", bold=True), err=True)


def print_warning(message: str) -> None:
    click.echo(click.style(f"\n⚠️  Warning: {message}", fg="yellow"), err=True)


def print_info(message: str) -> None:
    click.echo(click.style(message, fg="blue"))


@click.command()
@click.argument('description', required=False)
@click.option(
    '-f', '--file',
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help='Path to text/markdown file containing process description'
)
@click.option(
    '-o', '--output',
    default='process_diagram.bpmn',
    type=click.Path(dir_okay=False, writable=True),
    help='Output BPMN file path (default: process_diagram.bpmn)',
    show_default=True
)
@click.version_option(version='1.0.0', prog_name='💡Text2BPMN')
@click.help_option('-h', '--help')
def cli(description: Optional[str], file: Optional[str], output: str):
    """
    Convert natural language process descriptions to BPMN 2.0 diagrams.
    
    Provide either a description as plain text or use --file to read from a [.txt, .md] file.
    
    \b
    Examples:
      text2bpmn "User logs in, system validates, show dashboard"
      text2bpmn --file process.txt
      text2bpmn --file process.md --output diagram.bpmn
    """    
    
    # Validate that either description or file is provided
    if not file and not description:
        click.echo(click.get_current_context().get_help())
        click.echo(click.style("\nError: Please provide either a description or use --file option.", 
                              fg="red", bold=True), err=True)
        sys.exit(1)
    
    try:
        # Setup
        api_key = validate_api_key()
        llm_config = get_model_config()
        process_description = read_process_description(description, file)
        
        display_header(process_description)
        
        # Initialize services
        llm_service = LLMService(api_key, llm_config)
        bpmn_service = BPMNGeneratorService(llm_service)

        
        # Generate reasoning
        # click.echo(click.style("\n🔍 Analyzing process structure...", fg="white"))
        # reasoning = bpmn_service.generate_reasoning(process_description)
        # click.echo(click.style("\n📋 Reasoning:", fg="yellow", bold=True))
        # click.echo(reasoning)
        # click.echo("\n" + "-" * 70)
        
        click.echo(click.style("\n⚙️  Generating BPMN diagram...", fg="white"))
        bpmn_xml = bpmn_service.generate_bpmn(process_description)
        bpmn_service.save_bpmn(bpmn_xml, output)
        
        display_footer(output)
        
    except KeyboardInterrupt:
        click.echo(click.style("\n\n⚠️  Process interrupted by user.", fg="yellow"), err=True)
        sys.exit(130)
    except BPMNGenerationError as e:
        print_error(f"BPMN Generation Failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)
