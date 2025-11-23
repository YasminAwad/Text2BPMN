import re, json
import logging
from typing import Dict, Any, List
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from ..utils.prompt import retrieve_prompt
from .llm import LLMService
from .validator import BPMNFileValidator
from ..exceptions import BPMNGenerationError, BPMNLayoutError
from .layout import BPMNLayoutService
from .merger import BPMNMerger


class BPMNGeneratorService:
    def __init__(self, llm_service: LLMService):
        """Main service orchestrating BPMN generation pipeline."""
        
        self.llm_service = llm_service
        self.validator = BPMNFileValidator()
        self.merger = BPMNMerger()
        try:
            self.layout_service = BPMNLayoutService()
            logging.info("Auto-layout enabled")
        except BPMNLayoutError as e:
            logging.error(f"Auto-layout service initialization failed: {e}")
            raise BPMNGenerationError("Failed to generate BPMN file")


    def generate_bpmn(self, process_description: SyntaxError) -> str:
        """
        Generate BPMN XML from natural language description.
        
        Args:
            process_description: Natural language process description
            
        Returns:
            Valid BPMN 2.0 XML string
        """
        logging.info("Starting BPMN generation")

        ## STEP 1: generate json
        prompt_content = retrieve_prompt("01_generate_json.txt")
        logging.debug("Prompt content:\n%s", prompt_content)
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt_content)
            ])
        logging.debug("Prompt template:\n%s", prompt_template)
        json_content =  self.llm_service.run_prompt(prompt_template, {"process_description": process_description})
        logging.debug("JSON LLM response:\n%s", json_content)

        try:
            json_loaded =json.loads(json_content)
            json_bpmn = json_loaded["bpmn"]
            reasoning = json_loaded["reasoning"]

        except (ValueError, TypeError):
            logging.error("The response is not a valid JSON object or does not contain a 'process' key.")
            raise BPMNGenerationError("Failed to generate BPMN file")

        ## STEP 2: Extract lanes

        try:
            same_flow, different_flow = self.extract_all_sequence_flows(json_bpmn)
        except Exception as e:
            logging.error("Failed to extract sequence flows: %s", str(e))
            raise BPMNGenerationError("Failed to generate BPMN file")
        logging.debug("Same flow:\n%s", same_flow)
        logging.debug("Different flow:\n%s", different_flow)

        try:

            lanes =self.extract_all_lanes(json_bpmn, same_flow)
        except Exception as e:
            logging.error("Failed to extract lanes: %s", str(e))
            raise BPMNGenerationError("Failed to generate BPMN file")
        logging.debug("Lanes:\n%s", lanes)

        ## STEP 3: Generate BPMN XML for each lane
        laid_out_lanes = []

        i=0
        for lane in lanes:

            logging.debug("Lane number %d:\n%s", i, lane)

            logging.debug("Lane with flows:\n%s", lane)
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
            str_lane_process = json.dumps(lane_process)

            lane_prompt = retrieve_prompt("02_generate_little_xml.txt")
            lane_prompt_template = ChatPromptTemplate.from_messages([
                ("system", lane_prompt)
            ])
        
            lane_xml = self.llm_service.run_prompt(lane_prompt_template, {
                "json_lane": str_lane_process
            })
            
            logging.debug("LANE XML LLM response:\n%s", lane_xml)
            lane_xml_file_match = re.search(r"<file>(.*?)</file>", lane_xml, re.DOTALL)
            if not lane_xml_file_match:
                logging.error("The response does not contain a valid xml BPMN file.")
                raise BPMNGenerationError("Failed to generate BPMN file")
            lane_raw_xml = lane_xml_file_match.group(1).strip()

            logging.debug("Validating XML...")
            cleaned_lane_xml = self.validator.clean_xml(lane_raw_xml)
            self.validator.validate(cleaned_lane_xml)

            ## STEP 4 : Auto-layout for each lane
            try:
                laid_out_xml = self.layout_service.apply_layout(cleaned_lane_xml)
                logging.info("Lane Auto-layout applied successfully")
            except BPMNLayoutError as e:
                logging.error(f"Lane Auto-layout failed, using original: {e}")
                raise BPMNGenerationError("Failed to generate BPMN file")
            
            ## ADDING LANE DIAGRAM
            lane_with_diagram = self.merger.add_lane_diagram(laid_out_xml)

            # Store 
            laid_out_lanes.append(lane_with_diagram)

            logging.debug("Laid out XML:\n%s", lane_with_diagram)

            self.save_bpmn(laid_out_xml, f"/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/lanes/add_lane_diagram/lane_{i}.bpmn")

            i=i+1
        
        ## STEP 5: merge the lanes in unique xml

        merged_xml = self.merger.merge_bpmn_files(laid_out_lanes)
        self.save_bpmn(merged_xml, f"/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/lanes/merged.bpmn")

        merged_with_flows = self.merger.add_sequence_flows_from_json(merged_xml,different_flow)

        ## STEP 6: add inter-lane sequence flows asking the LLM

        

        logging.info("XML generation completed successfully")




        return merged_with_flows, reasoning # bpmn_xml
    
    def save_bpmn(self, bpmn_xml: str, save_path: str) -> None:
        """
        Save BPMN XML to file.
        
        Args:
            bpmn_xml: Valid BPMN XML content
            save_path: Path where to save the file
            
        Raises:
            BPMNGenerationError: If file cannot be saved
        """
        try:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(bpmn_xml)
                
        except Exception as e:
            raise BPMNGenerationError(f"Failed to save BPMN file: {str(e)}")



    def extract_all_lanes(self, json_bpmn: dict, same_flow: dict) -> List[dict]:

        lanes = []

        for lane in json_bpmn["process"]["pool"]["lanes"]:

            self.add_flows_to_lane(lane, same_flow)
            
            # add mock start and end events if not present
            if not any(element["type"] == "startEvent" for element in lane["elements"]):
                lane["elements"].insert(0, {
                    "id": "mock_start_event",
                    "type": "startEvent",
                    "name": "mock start",
                    "eventType": "none"
                    })
                
                lane["sequenceFlows"].insert(0, {
                    "id": "mock_start_event_flow",
                    "sourceRef": lane["elements"][0]["id"],
                    "targetRef": lane["elements"][1]["id"]
                    })
                
            if not any(element["type"] == "endEvent" for element in lane["elements"]):
                lane["elements"].append({
                    "id": "mock_end_event",
                    "type": "endEvent",
                    "name": "mock end",
                    "eventType": "none"
                    })
                
                lane["sequenceFlows"].append({
                    "id": "end_event_flow",
                    "sourceRef": lane["elements"][-2]["id"],
                    "targetRef": lane["elements"][-1]["id"]
                    })

            lanes.append(lane)
        return lanes
    
    def extract_all_sequence_flows(self, json_bpmn: dict):
        sequence_flows = json_bpmn["process"]["pool"]["sequenceFlows"]
        lanes = json_bpmn["process"]["pool"]["lanes"]

        # Prepare output structure
        same_flow = {"sequenceFlows": {}}     # dict of lane_id → list of flows
        different_flow = {"sequenceFlows": []}

        # Prebuild a mapping element_id → lane_id for performance
        element_to_lane = {}
        for lane in lanes:
            for element in lane["elements"]:
                element_to_lane[element["id"]] = lane["id"]

        for flow in sequence_flows:
            source_lane = element_to_lane.get(flow["sourceRef"])
            target_lane = element_to_lane.get(flow["targetRef"])

            if source_lane and target_lane and source_lane == target_lane:
                # Initialize list for this lane if needed
                if source_lane not in same_flow["sequenceFlows"]:
                    same_flow["sequenceFlows"][source_lane] = []

                same_flow["sequenceFlows"][source_lane].append(flow)
            else:
                different_flow["sequenceFlows"].append(flow)

        """
        same_flow = {
            "sequenceFlows": {
                "lane_customer_service_1": [flow_1, flow_2, ...],
                "lane_management_1": [flow_10, flow_11, ...]
            }
        }

        different_flow = {
            "sequenceFlows": [flow_9, flow_12, flow_14]
        }"""

        return same_flow, different_flow

    def add_flows_to_lane(self, lane: dict, sequence_flow: dict):
        """
        Adds the sequence flows belonging to a specific lane into the lane dict.
        'sequence_flow' is expected to be the 'same_flow' structure:
        {
            "sequenceFlows": {
                "lane_id": [flow1, flow2, ...]
            }
        }
        """
        lane_id = lane["id"]

        # Get flows for this lane, or empty list if none exist
        flows_for_lane = sequence_flow["sequenceFlows"].get(lane_id, [])

        # Ensure the lane has a sequenceFlows list
        if "sequenceFlows" not in lane:
            lane["sequenceFlows"] = []

        # Extend lane with all flows
        lane["sequenceFlows"].extend(flows_for_lane)

    
    # def add_flows_to_lane(self, lane: dict, sequence_flow: dict): # same flow sequence flows only
    #     # search flow of the lane and add it to the lane
    #     try:
    #         for flow in sequence_flow["sequenceFlows"][lane["id"]]:
    #             lane["sequenceFlows"].append(flow)
    #     except KeyError:
    #         logging.debug(f"No flow found for lane {lane['id']}")
        
