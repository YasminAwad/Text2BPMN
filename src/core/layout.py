import logging
import subprocess
from pathlib import Path
from typing import Optional

from ..exceptions import BPMNLayoutError


class BPMNLayoutService:
    """Service for applying automatic layout to BPMN diagrams of single lanes using Node.js subprocess."""
    
    def __init__(self, node_script_path: Optional[str] = None):
        """
        Initialize BPMN layout service.
        
        Args:
            node_script_path: Path to layout.js script. 
        """
        if node_script_path:
            self.script_path = Path(node_script_path)
        else:
            self.script_path = self._default_layout_script()

        if not self.script_path.exists():
            raise BPMNLayoutError(f"Layout script not found: {self.script_path}\n")
        
        self._verify_nodejs()
        
        logging.debug(f"Layout service initialized with script: {self.script_path}")
    
    def _default_layout_script(self) -> Path:
        """Default layout script location."""
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        
        return project_root / "layout_service" / "layout.js"
    
    def _verify_nodejs(self) -> None:
        """Verify Node.js is installed and available."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise BPMNLayoutError("Node.js is not available")
            
            logging.debug(f"Node.js version: {result.stdout.strip()}")
            
        except FileNotFoundError:
            raise BPMNLayoutError("Node.js is not installed or not in PATH.\n")
        except subprocess.TimeoutExpired:
            raise BPMNLayoutError("Node.js verification timed out")
    
    def apply_layout(self, bpmn_xml: str) -> str:
        """
        Apply automatic layout to BPMN XML (bpmn-auto-layout library).
        
        Args:
            bpmn_xml: BPMN XML string 
        
        Returns:
            BPMN XML string with layout information (positions, sizes)
        """
        logging.info("Applying auto-layout to BPMN diagram of the lane...")
        
        try:
            # Call Node.js script with BPMN XML as stdin
            result = subprocess.run(
                ["node", str(self.script_path)],
                input=bpmn_xml,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                logging.error(f"Layout script failed: {error_msg}")
                raise BPMNLayoutError(f"Auto-layout failed: {error_msg}")
            
            layouted_xml = result.stdout
            
            # Validate output
            if not layouted_xml or len(layouted_xml) < len(bpmn_xml) * 0.8:
                logging.error("Layout output is suspiciously small")
                raise BPMNLayoutError("Auto-layout produced invalid output")
            
            logging.info("Auto-layout applied successfully")
            
            return layouted_xml
            
        except subprocess.TimeoutExpired:
            logging.error("Layout operation timed out")
            raise BPMNLayoutError("Auto-layout timed out after 60 seconds. ")
        except FileNotFoundError:
            logging.error(f"Node.js or script not found: {self.script_path}")
            raise BPMNLayoutError(
                f"Failed to execute layout script.\n"
                f"Make sure Node.js is installed and npm dependencies are installed."
            )
        except Exception as e:
            logging.exception("Unexpected error during layout")
            raise BPMNLayoutError(f"Unexpected error during auto-layout: {str(e)}")
