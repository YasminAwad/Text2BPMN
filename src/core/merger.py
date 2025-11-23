import copy
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple

from ..exceptions import BPMNGenerationError, DiagramError
from .layout import BPMNLayoutService


class BPMNDiagramHelper:
    """Class to handle merging multiple BPMN lane files into one."""
    
    def __init__(self):
        self.namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'dc': 'http://www.omg.org/spec/DD/20100524/DC',
            'di': 'http://www.omg.org/spec/DD/20100524/DI',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }      

        # Register namespaces to preserve prefixes
        for prefix, uri in self.namespaces.items():
            ET.register_namespace(prefix, uri)

        try:
            self.layout_service = BPMNLayoutService()
            logging.info("Auto-layout enabled")
        except DiagramError as e:
            logging.error(f"Auto-layout service initialization failed: {e}")
            raise
        except Exception as e:
            logging.error(f"Auto-layout service initialization failed: {e}")
            raise

    def merge_lanes(self, lanes_xmls: List[str], diff_lane_flows: List[Dict], pool_name: str = "Pool/Participant"):
        """Merge multiple BPMN lane xmls into one.
        - For each lane, apply layout and add a shape to it.
        - Merge all lanes into one xml file.
        - Add sequence flows that connect elements of different lanes.
        - Add the pool layout (collaboration)
        
        Args:
            lanes_xmls: List of BPMN lane xmls
            diff_lane_flows: List of seequence flows between different lanes
            pool_name: Name of the process pool
        Returns:
            Merged BPMN xml
        """
        try:
            set_lanes = []
            for i, lane in enumerate(lanes_xmls):

                logging.info(f"Modifying lane {i}:")
                laid_out_xml = self.layout_service.apply_layout(lane)
                shaped_lane = self.add_lane_shape(laid_out_xml)

                set_lanes.append(shaped_lane)
            
            merged_xml = self.merge_xml_lanes(set_lanes)

            merged_with_flows = self.add_sequence_flows_from_json(merged_xml,
                                                                  diff_lane_flows)

            complete_xml = self.add_pool_to_bpmn(merged_with_flows,
                                                 pool_name)

        except DiagramError as e:
            logging.error(f"Error creating Diagram for multiple lanes: {e}")
            raise
        except BPMNGenerationError as e:
            logging.error(f"Auto-layout service initialization failed: {e}")
            raise
        except Exception as e:
            logging.exception(f"Error merging BPMN files: {e}")
            raise

        return complete_xml
    
    def add_lane_shape(self, single_lane_xml):
        """
        Add lane shape information to a BPMN XML file.
        """
        logging.info("Adding lane shape...")
        tree = ET.ElementTree(ET.fromstring(single_lane_xml))
        root = tree.getroot()

        lanes = root.findall('.//bpmn:lane', self.namespaces)
        bpmn_plane = root.find('.//bpmndi:BPMNPlane', self.namespaces)
        
        if bpmn_plane is None:
            logging.error("No BPMNPlane element found in the XML")
            return ET.tostring(root, encoding='unicode', xml_declaration=True)
        
        for lane in lanes:
            lane_id = lane.get('id')
            # Get all flowNodeRef elements (references to elements in the lane)
            flow_node_refs = lane.findall('bpmn:flowNodeRef', self.namespaces)
            
            if not flow_node_refs:
                logging.error(f"No flowNodeRef elements found in lane {lane_id}")
                continue
            
            # Collect bounds of all elements in the lane
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            
            for flow_node_ref in flow_node_refs:
                element_id = flow_node_ref.text
                
                # Find the corresponding shape in the diagram
                shape = bpmn_plane.find(f".//bpmndi:BPMNShape[@bpmnElement='{element_id}']", self.namespaces)
                
                if shape is not None:
                    bounds = shape.find('dc:Bounds', self.namespaces)
                    if bounds is not None:
                        x = float(bounds.get('x', 0))
                        y = float(bounds.get('y', 0))
                        width = float(bounds.get('width', 0))
                        height = float(bounds.get('height', 0))
                        
                        # Update min/max values
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x + width)
                        max_y = max(max_y, y + height)
            
            # Check if we found any valid bounds
            if min_x == float('inf'):
                logging.debug(f"Could not find any valid bounds for lane {lane_id}")
                continue
            
            # Calculate lane dimensions
            height_sum = max_y - min_y
            width_sum = max_x - min_x  # Fixed: was max_x - max_y
            
            lane_x = min_x - 60
            lane_y = min_y - 60
            lane_width = width_sum + 120
            lane_height = height_sum + 120
            
            # Check if lane shape already exists
            existing_shape = bpmn_plane.find(f".//bpmndi:BPMNShape[@bpmnElement='{lane_id}']", self.namespaces)
            
            if existing_shape is not None:
                # Update existing shape
                bounds = existing_shape.find('dc:Bounds', self.namespaces)
                if bounds is not None:
                    bounds.set('x', str(lane_x))
                    bounds.set('y', str(lane_y))
                    bounds.set('width', str(lane_width))
                    bounds.set('height', str(lane_height))
            else:
                # Create new lane shape element
                lane_shape = ET.Element(f'{{{self.namespaces["bpmndi"]}}}BPMNShape')
                lane_shape.set('id', f'{lane_id}_di')
                lane_shape.set('bpmnElement', lane_id)
                lane_shape.set('isHorizontal', 'true')
                
                # Create bounds element
                bounds = ET.SubElement(lane_shape, f'{{{self.namespaces["dc"]}}}Bounds')
                bounds.set('x', str(lane_x))
                bounds.set('y', str(lane_y))
                bounds.set('width', str(lane_width))
                bounds.set('height', str(lane_height))
                
                # Insert the lane shape at the beginning of BPMNPlane
                bpmn_plane.insert(0, lane_shape)
        
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def merge_xml_lanes(self, lanes_xml: List[str]):
        """
        Merge multiple BPMN lane files into one.
        """
        if not lanes_xml:
            raise ValueError("No files provided for merging")
        
        logging.info("Merging BPMN lanes...")

        base_tree = ET.ElementTree(ET.fromstring(lanes_xml[0]))
        base_root = base_tree.getroot()
        base_process = base_root.find('.//bpmn:process', self.namespaces)
        base_plane = base_root.find('.//bpmndi:BPMNPlane', self.namespaces)
        
        if base_process is None or base_plane is None:
            raise ValueError("Base file must contain process and BPMNPlane elements")
        
        # Remove mock elements from base file
        self._remove_mock_elements(base_root, base_process)
        
        # Get base lane info
        base_laneset = base_process.find('.//bpmn:laneSet', self.namespaces)
        if base_laneset is None:
            raise ValueError("Base file must contain a laneSet")
        
        base_lane = base_laneset.find('.//bpmn:lane', self.namespaces)
        base_lane_id = base_lane.get('id')
        base_lane_bounds = self._get_lane_bounds(base_plane, base_lane_id)
        
        if base_lane_bounds is None:
            raise ValueError(f"Could not find bounds for base lane: {base_lane_id}")

        current_y_offset = base_lane_bounds['y']
        current_height = base_lane_bounds['height']
        max_width = base_lane_bounds['width']
        
        # Process each additional file
        for i, single_lane_xml in enumerate(lanes_xml[1:], 1):
            
            # Parse the file to merge
            merge_tree = ET.ElementTree(ET.fromstring(single_lane_xml))
            merge_root = merge_tree.getroot()
            merge_process = merge_root.find('.//bpmn:process', self.namespaces)
            merge_plane = merge_root.find('.//bpmndi:BPMNPlane', self.namespaces)
            
            if merge_process is None or merge_plane is None:
                logging.info(f"Skipping {single_lane_xml}: no process or BPMNPlane found")
                continue
            
            # Remove mock elements
            self._remove_mock_elements(merge_root, merge_process)
            
            # Get merge lane info
            merge_laneset = merge_process.find('.//bpmn:laneSet', self.namespaces)
            if merge_laneset is None:
                logging.info(f"Skipping {single_lane_xml}: no laneSet found")
                continue
            
            merge_lane = merge_laneset.find('.//bpmn:lane', self.namespaces)
            merge_lane_id = merge_lane.get('id')
            merge_lane_bounds = self._get_lane_bounds(merge_plane, merge_lane_id)
            
            if merge_lane_bounds is None:
                logging.info(f"Skipping {single_lane_xml}: could not find bounds for merge lane: {merge_lane_id}")
                continue

            # Calculate gaps and new positions
            x_gap = merge_lane_bounds['x'] - base_lane_bounds['x']
            new_lane_B_y = current_y_offset + current_height
            y_gap = merge_lane_bounds['y'] - new_lane_B_y
            
            # Update max width
            max_width = max(max_width, merge_lane_bounds['width'])
            
            # Adjust coordinates in merge_plane
            self._adjust_diagram_coordinates(merge_plane, merge_lane_id, x_gap, y_gap)
            
            # Update lane bounds
            merge_lane_shape = merge_plane.find(
                f".//bpmndi:BPMNShape[@bpmnElement='{merge_lane_id}']",
                self.namespaces
            )
            if merge_lane_shape is not None:
                merge_bounds = merge_lane_shape.find('dc:Bounds', self.namespaces)
                if merge_bounds is not None:
                    merge_bounds.set('x', str(base_lane_bounds['x']))
                    merge_bounds.set('y', str(new_lane_B_y))
                    merge_bounds.set('width', str(max_width))
            
            # Add lane to base laneSet
            base_laneset.append(copy.deepcopy(merge_lane))
            
            # Add all process elements (except laneSet) to base process
            for element in merge_process:
                tag = element.tag.split('}')[-1]  # Get tag without namespace
                if tag != 'laneSet':
                    base_process.append(copy.deepcopy(element))
            
            # Add all diagram elements to base plane
            for element in merge_plane:
                tag = element.tag.split('}')[-1]
                if tag in ['BPMNShape', 'BPMNEdge']:
                    base_plane.append(copy.deepcopy(element))
            
            # Update current position for next lane
            current_y_offset = new_lane_B_y
            current_height = merge_lane_bounds['height']
        
        # Update all lane widths to max_width
        for lane_shape in base_plane.findall('.//bpmndi:BPMNShape[@isHorizontal="true"]', self.namespaces):
            bounds = lane_shape.find('dc:Bounds', self.namespaces)
            if bounds is not None:
                bounds.set('width', str(max_width))
        
        merged_xml_string = ET.tostring(base_root, encoding='unicode', xml_declaration=True)
        return merged_xml_string
    
    def add_sequence_flows_from_json(self, single_lane_xml, sequence_flows_json):
        """
        Add sequence flows from JSON to a BPMN XML file.
        
        Args:
            single_lane_xml: BPMN XML string
            sequence_flows_json: Dictionary containing 'sequenceFlows' list
            output_file_path: Path to save the modified XML (if None, overwrites input)
        
        Returns:
            The modified XML tree
        
        Example JSON format:
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
        logging.info("Adding sequence flows from JSON...")
        tree = ET.ElementTree(ET.fromstring(single_lane_xml))
        root = tree.getroot()
        
        process = root.find('.//bpmn:process', self.namespaces)
        bpmn_plane = root.find('.//bpmndi:BPMNPlane', self.namespaces)
        
        if process is None:
            raise ValueError("Process element not found in BPMN file")
        
        if bpmn_plane is None:
            raise ValueError("BPMNPlane element not found in BPMN file")
        
        sequence_flows = sequence_flows_json.get('sequenceFlows', [])
        
        if not sequence_flows:
            return ET.tostring(root, encoding='unicode', xml_declaration=True)
        
        for flow_data in sequence_flows:
            flow_id = flow_data.get('id')
            source_ref = flow_data.get('sourceRef')
            target_ref = flow_data.get('targetRef')
            
            if not flow_id or not source_ref or not target_ref:
                logging.debug("Invalid sequence flow data, skipping")
                continue
            
            # Check if sequence flow already exists
            existing_flow = process.find(f".//bpmn:sequenceFlow[@id='{flow_id}']", self.namespaces)
            if existing_flow is not None:
                logging.debug(f"Sequence flow {flow_id} already exists, skipping")
                continue
            
            # Find source and target elements in the diagram
            source_shape = bpmn_plane.find(
                f".//bpmndi:BPMNShape[@bpmnElement='{source_ref}']",
                self.namespaces
            )
            target_shape = bpmn_plane.find(
                f".//bpmndi:BPMNShape[@bpmnElement='{target_ref}']",
                self.namespaces
            )
            
            if source_shape is None:
                logging.debug(f"Source element {source_ref} not found in diagram, skipping flow {flow_id}")
                continue
            
            if target_shape is None:
                logging.debug(f"Target element {target_ref} not found in diagram, skipping flow {flow_id}")
                continue
            
            # Get bounds of source and target
            source_bounds = source_shape.find('dc:Bounds', self.namespaces)
            target_bounds = target_shape.find('dc:Bounds', self.namespaces)
            
            if source_bounds is None or target_bounds is None:
                logging.debug(f"Bounds not found for source or target element, skipping flow {flow_id}")
                continue
            
            # Extract coordinates
            source_x = float(source_bounds.get('x', 0))
            source_y = float(source_bounds.get('y', 0))
            source_width = float(source_bounds.get('width', 0))
            source_height = float(source_bounds.get('height', 0))
            
            target_x = float(target_bounds.get('x', 0))
            target_y = float(target_bounds.get('y', 0))
            target_width = float(target_bounds.get('width', 0))
            target_height = float(target_bounds.get('height', 0))
            
            # Calculate waypoints
            waypoint_1_x = round(source_x + source_width / 2)
            waypoint_2_x = round(target_x + target_width / 2)
            
            # Determine waypoint y coordinates based on relative positions
            if source_y < target_y:
                # Source is above target
                waypoint_1_y = round(source_y + source_height)
                waypoint_2_y = round(target_y)
            else:
                # Source is below or at same level as target
                waypoint_1_y = round(source_y)
                waypoint_2_y = round(target_y + target_height)
            
            # Create sequence flow element in process
            sequence_flow = ET.Element(f'{{{self.namespaces["bpmn"]}}}sequenceFlow')
            sequence_flow.set('id', flow_id)
            sequence_flow.set('sourceRef', source_ref)
            sequence_flow.set('targetRef', target_ref)
            
            # Add sequence flow to process
            process.append(sequence_flow)
            
            # Create BPMNEdge for diagram
            bpmn_edge = ET.Element(f'{{{self.namespaces["bpmndi"]}}}BPMNEdge')
            bpmn_edge.set('id', f'{flow_id}_di')
            bpmn_edge.set('bpmnElement', flow_id)
            
            # Add first waypoint
            waypoint_1 = ET.SubElement(bpmn_edge, f'{{{self.namespaces["di"]}}}waypoint')
            waypoint_1.set('x', str(waypoint_1_x))
            waypoint_1.set('y', str(waypoint_1_y))
            
            # Add second waypoint
            waypoint_2 = ET.SubElement(bpmn_edge, f'{{{self.namespaces["di"]}}}waypoint')
            waypoint_2.set('x', str(waypoint_2_x))
            waypoint_2.set('y', str(waypoint_2_y))
            
            # Add edge to BPMNPlane
            bpmn_plane.append(bpmn_edge)

        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def add_pool_to_bpmn(self, xml_content, main_actor):
        """
        Adds a pool representation (collaboration element and diagram update) to a BPMN XML file.
        
        Args:
            xml_content (str): BPMN XML string.
            main_actor (str): Name of the pool
        
        Returns:
            BPMN XML string with poll diagram (collaboration) added.
        """
        logging.info("Adding pool to BPMN...")
        # Parse the XML file
        tree = ET.ElementTree(ET.fromstring(xml_content))
        root = tree.getroot()
        
        # Define namespaces
        namespaces = self.namespaces
        
        # # Register namespaces to preserve prefixes
        # for prefix, uri in namespaces.items():
        #     ET.register_namespace(prefix, uri)
        
        # Extract process id and name
        process = root.find('bpmn:process', namespaces)
        if process is None:
            raise ValueError("No bpmn:process element found in the XML")
        
        process_id = process.get('id')
        participant_name = main_actor  # Use id as fallback if name not present
        
        # Set collaboration and participant IDs
        participant_id = "process_participant_1"
        collaboration_id = "bpmnElement_of_the_Plane_1"
        
        # Check if collaboration already exists
        existing_collab = root.find('bpmn:collaboration', namespaces)
        if existing_collab is not None:
            root.remove(existing_collab)
        
        # Create collaboration element
        collaboration = ET.Element(f"{{{namespaces['bpmn']}}}collaboration")
        collaboration.set('id', collaboration_id)
        
        # Create participant element
        participant = ET.Element(f"{{{namespaces['bpmn']}}}participant")
        participant.set('id', participant_id)
        participant.set('name', participant_name)
        participant.set('processRef', process_id)
        
        # Add participant to collaboration
        collaboration.append(participant)
        
        # Insert collaboration before process element
        process_index = list(root).index(process)
        root.insert(process_index, collaboration)
        
        # Update BPMNPlane bpmnElement attribute and add participant shape
        bpmn_diagram = root.find('bpmndi:BPMNDiagram', namespaces)
        if bpmn_diagram is not None:
            bpmn_plane = bpmn_diagram.find('bpmndi:BPMNPlane', namespaces)
            if bpmn_plane is not None:
                bpmn_plane.set('bpmnElement', collaboration_id)
                
                # Add participant shape
                self._add_participant_shape(bpmn_plane, process, participant_id, namespaces)
            else:
                logging.debug("BPMNPlane element not found")
        else:
            logging.debug("BPMNDiagram element not found")
  
        return ET.tostring(root, encoding="unicode", xml_declaration=True)
    
    def _get_lane_bounds(self, bpmn_plane, lane_id: str) -> Dict:
        """Get the bounds of a lane from the diagram."""
        lane_shape = bpmn_plane.find(
            f".//bpmndi:BPMNShape[@bpmnElement='{lane_id}']", 
            self.namespaces
        )
        
        if lane_shape is not None:
            bounds = lane_shape.find('dc:Bounds', self.namespaces)
            if bounds is not None:
                return {
                    'x': float(bounds.get('x', 0)),
                    'y': float(bounds.get('y', 0)),
                    'width': float(bounds.get('width', 0)),
                    'height': float(bounds.get('height', 0))
                }
        return None
    
    def _adjust_diagram_coordinates(self, bpmn_plane, lane_id: str, x_gap: float, y_gap: float):
        """Adjust coordinates of all diagram elements in a lane."""
        # Adjust shapes
        for shape in bpmn_plane.findall('.//bpmndi:BPMNShape', self.namespaces):
            bounds = shape.find('dc:Bounds', self.namespaces)
            if bounds is not None:
                x = float(bounds.get('x', 0))
                y = float(bounds.get('y', 0))
                
                new_x = x - x_gap
                new_y = y - y_gap
                
                bounds.set('x', str(new_x))
                bounds.set('y', str(new_y))
        
        # Adjust edges
        for edge in bpmn_plane.findall('.//bpmndi:BPMNEdge', self.namespaces):
            for waypoint in edge.findall('.//di:waypoint', self.namespaces):
                x = float(waypoint.get('x', 0))
                y = float(waypoint.get('y', 0))
                
                new_x = x - x_gap
                new_y = y - y_gap
                
                waypoint.set('x', str(new_x))
                waypoint.set('y', str(new_y))

    def _remove_mock_elements(self, root, process):
        """Remove mock start and end events from process and diagram."""
        elements_to_remove = []
        
        for element in process:
            element_id = element.get('id')
            if self._is_mock_element(element_id):
                elements_to_remove.append(element)
        
        # Remove mock elements from process
        for element in elements_to_remove:
            process.remove(element)
        
        # Remove mock elements from diagram
        bpmn_plane = root.find('.//bpmndi:BPMNPlane', self.namespaces)
        if bpmn_plane is not None:
            diagram_elements_to_remove = []
            
            for shape in bpmn_plane.findall('.//bpmndi:BPMNShape', self.namespaces):
                element_ref = shape.get('bpmnElement')
                if self._is_mock_element(element_ref):
                    diagram_elements_to_remove.append(shape)
            
            for edge in bpmn_plane.findall('.//bpmndi:BPMNEdge', self.namespaces):
                element_ref = edge.get('bpmnElement')
                if self._is_mock_element(element_ref):
                    diagram_elements_to_remove.append(edge)
            
            for element in diagram_elements_to_remove:
                bpmn_plane.remove(element)

    def _is_mock_element(self, element_id: str) -> bool:
        """Check if an element is a mock start or end event."""
        if element_id is None:
            return False
        return 'mock_start' in element_id.lower() or 'mock_end' in element_id.lower()
    
    def _add_participant_shape(self, bpmn_plane, process, participant_id, namespaces):
        """
        Adds a BPMNShape for the participant based on lane dimensions.
        """
        # Find all lanes in the process
        lane_set = process.find('bpmn:laneSet', namespaces)
        if lane_set is None:
            logging.debug("No laneSet found in process")
            return
        
        lanes = lane_set.findall('bpmn:lane', namespaces)
        if not lanes:
            logging.debug("No lanes found in laneSet")
            return
        
        # Collect lane dimensions from BPMNShape elements
        lane_bounds = []
        for lane in lanes:
            lane_id = lane.get('id')
            # Find the corresponding BPMNShape
            lane_shape = bpmn_plane.find(f".//bpmndi:BPMNShape[@bpmnElement='{lane_id}']", namespaces)
            if lane_shape is not None:
                bounds = lane_shape.find('dc:Bounds', namespaces)
                if bounds is not None:
                    x = float(bounds.get('x', 0))
                    y = float(bounds.get('y', 0))
                    width = float(bounds.get('width', 0))
                    height = float(bounds.get('height', 0))
                    lane_bounds.append({
                        'id': lane_id,
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height
                    })
        
        if not lane_bounds:
            logging.debug("No lane bounds found in diagram")
            return
        
        # Calculate participant shape dimensions
        min_x = min(lane['x'] for lane in lane_bounds)
        min_y = min(lane['y'] for lane in lane_bounds)
        sum_heights = sum(lane['height'] for lane in lane_bounds)
        first_lane_width = lane_bounds[0]['width']
        
        # Calculate final values according to specifications
        x_value = min_x - 30
        y_value = min_y
        width_value = first_lane_width + 30
        height_value = sum_heights
        
        # Create participant BPMNShape
        bpmnshape_id = "participant_shape_1"
        participant_shape = ET.Element(f"{{{namespaces['bpmndi']}}}BPMNShape")
        participant_shape.set('id', bpmnshape_id)
        participant_shape.set('bpmnElement', participant_id)
        participant_shape.set('isHorizontal', 'true')
        
        # Create dc:Bounds element
        bounds = ET.Element(f"{{{namespaces['dc']}}}Bounds")
        bounds.set('x', str(int(x_value)))
        bounds.set('y', str(int(y_value)))
        bounds.set('width', str(int(width_value)))
        bounds.set('height', str(int(height_value)))
        
        participant_shape.append(bounds)
        
        # Create empty BPMNLabel
        label = ET.Element(f"{{{namespaces['bpmndi']}}}BPMNLabel")
        participant_shape.append(label)
        
        # Insert participant shape as first element in BPMNPlane
        bpmn_plane.insert(0, participant_shape)


