import sys
import click
import logging

from typing import Optional

import src.config as config
from .utils.file_handler import read_process_description
from .core.llm import LLMService
from .core.generator import BPMNGeneratorService
from .exceptions import BPMNGenerationError


def display_header() -> None:
    click.echo("=" * 70)
    click.echo(click.style("💡Text2BPMN", fg="white", bold=True).center(80))
    click.echo("=" * 70)


def display_footer(output_path: str, reasoning: str) -> None:
    click.echo(f"\n✅ BPMN diagram saved to: {click.style(output_path, fg='bright_cyan')}")
    url = "http://demo.bpmn.io/"
    link = f"\033]8;;{url}\033\\bpmn.io\033]8;;\033\\"
    click.echo(f"\n➡️  You can drag and drop the .bpmn file at {link} for visualization\n\n")
    click.echo(click.style("📜 Reasoning Report:", fg="white", bold=True))
    click.echo(click.style(f"{reasoning}", fg="white"))


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
    Converts a natural-language process description
    into a valid BPMN 2.0 diagram (XML .bpmn file) using a Large Language Model (GPT-4.1)
    
    Provide either a description as plain text or use --file to read from a [.txt, .md] file.
    
    \b
    Examples:
      text2bpmn "User logs in, system validates, show dashboard"
      text2bpmn --file process.txt
      text2bpmn --file process.md --output diagram.bpmn
    """    
    if not file and not description:
        click.echo(click.get_current_context().get_help())
        click.echo(click.style("\nError: Please provide either a description or use --file option.", 
                              fg="red", bold=True), err=True)
        sys.exit(1)
    
    try:
        logging.info("Initializing services...")
        settings = config.load_settings()
        config.setup_logging(settings)

        api_key = config.get_api_key(settings)
        llm_config = config.get_model_config(settings)

        llm_service = LLMService(api_key, llm_config)
        bpmn_service = BPMNGeneratorService(llm_service)
        logging.info("Services initialized.")

        process_description = read_process_description(description, file)

        display_header()
        
        click.echo(click.style("\n⚙️  Generating BPMN diagram...", fg="white"))
        bpmn_xml, reasoning = bpmn_service.generate_bpmn(process_description)
        bpmn_service.save_bpmn(bpmn_xml, output)
        logging.info("BPMN diagram generated.")
        
        display_footer(output, reasoning)

        logging.info("Process completed.")
        
    except KeyboardInterrupt:
        click.echo(click.style("\n\n⚠️  Process interrupted by user.", fg="yellow"), err=True)
        sys.exit(130)
    except BPMNGenerationError as e:
        print_error(f"BPMN Generation Failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)
