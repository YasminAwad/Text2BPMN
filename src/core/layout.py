# src/core/layout.py
"""
BPMN Auto-Layout Service using Node.js subprocess.

This module provides automatic layout for BPMN diagrams using the
bpmn-auto-layout library via Node.js subprocess.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from ..exceptions import BPMNLayoutError

logger = logging.getLogger(__name__)


class BPMNLayoutService:
    """Service for applying automatic layout to BPMN diagrams."""
    
    def __init__(self, node_script_path: Optional[str] = None):
        """
        Initialize BPMN layout service.
        
        Args:
            node_script_path: Path to layout.js script. 
                            If None, auto-detects from project structure.
        """
        if node_script_path:
            self.script_path = Path(node_script_path)
        else:
            # Auto-detect script location
            self.script_path = self._find_layout_script()
        
        # Verify Node.js is available
        self._verify_nodejs()
        
        # Verify script exists
        if not self.script_path.exists():
            raise BPMNLayoutError(
                f"Layout script not found: {self.script_path}\n"
                f"Please run: npm install in the project root"
            )
        
        logger.debug(f"Layout service initialized with script: {self.script_path}")
    
    def _find_layout_script(self) -> Path:
        """Auto-detect layout script location."""
        # Try to find from current file location
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        
        # Try common locations
        possible_paths = [
            project_root / "layout_service" / "layout.js",
            project_root / "node_scripts" / "layout.js",
            project_root / "layout.js",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Default to layout_service/layout.js
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
            
            logger.debug(f"Node.js version: {result.stdout.strip()}")
            
        except FileNotFoundError:
            raise BPMNLayoutError(
                "Node.js is not installed or not in PATH.\n"
                "Please install Node.js from https://nodejs.org/"
            )
        except subprocess.TimeoutExpired:
            raise BPMNLayoutError("Node.js verification timed out")
    
    def apply_layout(self, bpmn_xml: str) -> str:
        """
        Apply automatic layout to BPMN XML.
        
        Args:
            bpmn_xml: BPMN XML string without layout information
        
        Returns:
            BPMN XML string with layout information (positions, sizes)
        
        Raises:
            BPMNLayoutError: If layout application fails
        
        Example:
            >>> service = BPMNLayoutService()
            >>> unlayouted = '<?xml version="1.0"?>...'
            >>> layouted = service.apply_layout(unlayouted)
            >>> # layouted now has waypoints, bounds, etc.
        """
        logger.info("Applying auto-layout to BPMN diagram")
        logger.debug(f"Input BPMN size: {len(bpmn_xml)} bytes")
        
        try:
            # Call Node.js script with BPMN XML as stdin
            result = subprocess.run(
                ["node", str(self.script_path)],
                input=bpmn_xml,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                logger.error(f"Layout script failed: {error_msg}")
                raise BPMNLayoutError(f"Auto-layout failed: {error_msg}")
            
            layouted_xml = result.stdout
            
            # Validate output
            if not layouted_xml or len(layouted_xml) < len(bpmn_xml) * 0.8:
                logger.error("Layout output is suspiciously small")
                raise BPMNLayoutError("Auto-layout produced invalid output")
            
            logger.info("Auto-layout applied successfully")
            logger.debug(f"Output BPMN size: {len(layouted_xml)} bytes")
            
            return layouted_xml
            
        except subprocess.TimeoutExpired:
            logger.error("Layout operation timed out")
            raise BPMNLayoutError(
                "Auto-layout timed out after 30 seconds. "
                "The BPMN diagram might be too complex."
            )
        except FileNotFoundError:
            logger.error(f"Node.js or script not found: {self.script_path}")
            raise BPMNLayoutError(
                f"Failed to execute layout script.\n"
                f"Make sure Node.js is installed and npm dependencies are installed:\n"
                f"  cd {self.script_path.parent}\n"
                f"  npm install"
            )
        except Exception as e:
            logger.exception("Unexpected error during layout")
            raise BPMNLayoutError(f"Unexpected error during auto-layout: {str(e)}")
    
    def apply_layout_to_file(self, input_path: str, output_path: str) -> None:
        """
        Apply auto-layout to a BPMN file.
        
        Args:
            input_path: Path to input BPMN file
            output_path: Path to output BPMN file
        
        Raises:
            BPMNLayoutError: If operation fails
        """
        logger.info(f"Applying layout: {input_path} -> {output_path}")
        
        input_file = Path(input_path)
        output_file = Path(output_path)
        
        if not input_file.exists():
            raise BPMNLayoutError(f"Input file not found: {input_path}")
        
        # Read input
        bpmn_xml = input_file.read_text(encoding='utf-8')
        
        # Apply layout
        layouted_xml = self.apply_layout(bpmn_xml)
        
        # Write output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(layouted_xml, encoding='utf-8')
        
        logger.info(f"Layouted BPMN saved to: {output_path}")


# Convenience function
def apply_auto_layout(bpmn_xml: str) -> str:
    """
    Convenience function to apply auto-layout.
    
    Args:
        bpmn_xml: BPMN XML string
    
    Returns:
        Layouted BPMN XML string
    """
    service = BPMNLayoutService()
    return service.apply_layout(bpmn_xml)