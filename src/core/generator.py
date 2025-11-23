import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

from .llm import LLMService
from .merger import BPMNDiagramHelper
from .validator import BPMNFileValidator
from ..exceptions import BPMNGenerationError


class BPMNGeneratorService:
    def __init__(self, llm_service: LLMService):
        """Main service orchestrating BPMN generation pipeline."""
        
        self.llm_service = llm_service
        self.validator = BPMNFileValidator()
        self.merger = BPMNDiagramHelper()

    def generate_bpmn(self, process_description: str) -> str:
        """
        Generate BPMN XML from natural language description.
        
        Args:
            process_description: Natural language process description
            
        Returns:
            Valid BPMN 2.0 XML string
        """
        logging.info("Starting BPMN generation:")

        try:
            ## STEP 1 - Generate JSON of the process with LLM
            logging.info("1. Generating JSON from LLM")

            json_content = self.llm_service.call_llm("01_generate_json.txt",
                                                     {"process_description": process_description})
            
            json_loaded =json.loads(json_content)

            json_bpmn = json_loaded["bpmn"]
            reasoning = json_loaded["reasoning"]
            same_flow, different_flow = self._extract_all_sequence_flows(json_bpmn)

            ## STEP 2 - Extract lanes
            logging.info("2. Extracting lanes from JSON")
            all_lanes =self._extract_all_lanes(json_bpmn, same_flow)
            logging.debug("Lanes:\n%s", all_lanes)

            ## STEP 3 - Generate BPMN XML for each lane 
            logging.info("3. Generating BPMN XML for each lane")
            xml_lanes_list = []

            for i, lane in enumerate(all_lanes):

                logging.debug("Lane number %d:\n%s", i, lane)

                lane_process = {
                    "process": {
                        "id": json_bpmn["process"]["id"],
                        "name": json_bpmn["process"]["name"],
                        "pool": {
                            "id": json_bpmn["process"]["pool"]["id"],
                            "name": json_bpmn["process"]["pool"]["name"],
                            "lanes": lane
                        }
                    }
                }
                
                json_lane_process = json.dumps(lane_process)
                
                lane_xml = self.llm_service.call_llm("02_generate_little_xml.txt",
                                                     {"json_lane": json_lane_process})
                
                lane_raw_xml = self._get_xml(lane_xml)
                cleaned_lane_xml = self.validator.clean_xml(lane_raw_xml)
                self.validator.validate(cleaned_lane_xml)

                xml_lanes_list.append(cleaned_lane_xml)

            # STEP 4 - Merge all BPMN XML into one
            logging.info("4. Merging Lanes into a single BPMN XML")
            pool_name = json_bpmn["process"]["pool"]["name"]
            complete_bpmn_xml = self.merger.merge_lanes(xml_lanes_list, 
                                                        different_flow, 
                                                        pool_name)

        except (ValueError, TypeError) as e:
            logging.error(f"Invalid JSON response from LLM: {e}")
            raise BPMNGenerationError(f"Failed to parse LLM response as JSON: {e}") from e
        except KeyError as e:
            logging.error(f"JSON response missing required key: {e}")
            raise BPMNGenerationError(f"LLM response missing required field: {e}") from e
        except BPMNGenerationError: 
            raise
        except Exception as e:
            logging.exception("Unexpected error during BPMN generation")
            raise BPMNGenerationError(f"Unexpected error: {e}") from e

        return complete_bpmn_xml, reasoning
    
    def save_bpmn(self, bpmn_xml: str, save_path: str) -> None:
        """
        Save BPMN XML to file.
        """
        try:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(bpmn_xml)
      
        except Exception as e:
            raise BPMNGenerationError(f"Failed to save BPMN file: {str(e)}")

    def _extract_all_sequence_flows(self, json_bpmn: Dict) -> Tuple[Dict, Dict]: 
        """
        Extracts and separates in 2 dicts all sequence flows from a full BPMN JSON.
        
        Input:
            json_bpmn: json containing a full BPMN process

        Output:
            same_flow: json containing all sequence flows that start and end in the same lane
            
            different_flow: json containing all sequence flows that start and end in different lanes
        """
        sequence_flows = json_bpmn["process"]["pool"]["sequenceFlows"]
        lanes = json_bpmn["process"]["pool"]["lanes"]

        same_flow = {"sequenceFlows": {}}
        different_flow = {"sequenceFlows": []}

        element_to_lane = {}
        for lane in lanes:
            for element in lane["elements"]:
                element_to_lane[element["id"]] = lane["id"]

        for flow in sequence_flows:
            source_lane = element_to_lane.get(flow["sourceRef"])
            target_lane = element_to_lane.get(flow["targetRef"])

            if source_lane and target_lane and source_lane == target_lane:
                if source_lane not in same_flow["sequenceFlows"]:
                    same_flow["sequenceFlows"][source_lane] = []
                same_flow["sequenceFlows"][source_lane].append(flow)
            else:
                different_flow["sequenceFlows"].append(flow)

        logging.debug("Same flow:\n%s", same_flow)
        logging.debug("Different flow:\n%s", different_flow)

        return same_flow, different_flow

    def _get_xml(self, llm_xml: Dict) -> str:
        lane_xml_file_match = re.search(r"<file>(.*?)</file>", llm_xml, re.DOTALL)
        if not lane_xml_file_match:
            logging.error("The response does not contain a valid xml BPMN file.")
            raise BPMNGenerationError("Failed to generate BPMN file.")
        lane_raw_xml = lane_xml_file_match.group(1).strip()
        return lane_raw_xml
    
    def _extract_all_lanes(self, json_bpmn: Dict, same_flow: Dict) -> List[Dict]:
        """
        Extract all lanes from a full BPMN JSON, giving each lane its sequence flows. Mock start and end events (and mock sequence flows) are added if not present in order to create standalone lanes.

        Input:
            json_bpmn: json containing a full BPMN process
            same_flow: json containing all sequence flows that start and end in the same lane

        Output:
            all_lanes_with_flows: List of lanes (dicts)
        """
        all_lanes_with_flows = []

        for lane in json_bpmn["process"]["pool"]["lanes"]:
            lane_id = lane["id"]
            flows_for_lane = same_flow["sequenceFlows"].get(lane_id, [])
            self._add_flows_to_lane(lane, flows_for_lane)

            # Add mock start
            if not any(element["type"] == "startEvent" for element in lane["elements"]):
                lane["elements"].insert(0, {
                    "id": "mock_start_event",
                    "type": "startEvent",
                    "name": "mock start",
                    "eventType": "none"
                    })
                
                lane["sequenceFlows"].insert(0, {
                    "id": "mock_start_event_flow",
                    "sourceRef": lane["elements"][0]["id"], # from mock start
                    "targetRef": lane["elements"][1]["id"] # to first element
                    })
                
            # Add mock end
            if not any(element["type"] == "endEvent" for element in lane["elements"]):
                lane["elements"].append({
                    "id": "mock_end_event",
                    "type": "endEvent",
                    "name": "mock end",
                    "eventType": "none"
                    })
                
                lane["sequenceFlows"].append({
                    "id": "end_event_flow",
                    "sourceRef": lane["elements"][-2]["id"], # from last element
                    "targetRef": lane["elements"][-1]["id"] # to mock end
                    })

            all_lanes_with_flows.append(lane)

        return all_lanes_with_flows
    
    def _add_flows_to_lane(self, lane: Dict, flows_for_lane: Dict) -> None:
        """
        Adds the sequence flows belonging to a specific lane into the lane dict.

        Example flows_for_lane JSON format:
        {
            'sequenceFlows': [
                {
                    'id': 'flow_9',
                    'sourceRef': 'task_escalate_issue_1',
                    'targetRef': 'task_investigate_critical_feedback_1'
                }
            ]
        }
        """
        if "sequenceFlows" not in lane:
            lane["sequenceFlows"] = []
        lane["sequenceFlows"].extend(flows_for_lane)
        
