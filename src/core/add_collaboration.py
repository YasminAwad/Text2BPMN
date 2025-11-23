import xml.etree.ElementTree as ET
from typing import Optional

def add_collaboration_to_bpmn(input_file: str, output_file: str) -> bool:
    """
    Adds a collaboration element to an existing BPMN XML file.
    
    Args:
        input_file: Path to the input BPMN XML file
        output_file: Path to save the modified BPMN XML file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Parse the XML file
        tree = ET.parse(input_file)
        root = tree.getroot()
        
        # Extract actual namespaces from the root element
        actual_namespaces = {}
        for prefix, uri in root.nsmap.items() if hasattr(root, 'nsmap') else {}:
            if prefix:
                actual_namespaces[prefix] = uri
        
        # Define default namespaces (try both common BPMN namespace formats)
        namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmn2': 'http://bpmn.io/schema/bpmn',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'dc': 'http://www.omg.org/spec/DD/20100524/DC',
            'di': 'http://www.omg.org/spec/DD/20100524/DI'
        }
        
        # Try to detect which BPMN namespace is used
        bpmn_ns = None
        for ns in ['http://www.omg.org/spec/BPMN/20100524/MODEL', 'http://bpmn.io/schema/bpmn']:
            if root.find('.//{%s}process' % ns) is not None:
                bpmn_ns = ns
                namespaces['bpmn'] = ns
                break
        
        # Register namespaces to preserve prefixes
        for prefix, uri in namespaces.items():
            try:
                ET.register_namespace(prefix if prefix != 'bpmn2' else 'bpmn', uri)
            except:
                pass
        
        # Find the process element
        process = root.find('.//bpmn:process', namespaces)
        if process is None:
            print(f"Error: No process element found in the BPMN file. Detected namespace: {bpmn_ns}")
            return False
        
        process_id = process.get('id')
        process_name = process.get('name', 'Process')
        
        # Find the BPMNPlane element to get collaboration ID
        plane = root.find('.//bpmndi:BPMNPlane', namespaces)
        if plane is None:
            print("Error: No BPMNPlane element found in the BPMN file")
            return False
        
        plane_bpmn_element = plane.get('bpmnElement')
        
        # Find the participant shape in the diagram to get participant ID
        participant_shape = root.find('.//bpmndi:BPMNShape[@bpmnElement]', namespaces)
        participant_id = None
        
        # Look for existing participant shape
        for shape in root.findall('.//bpmndi:BPMNShape', namespaces):
            bpmn_element = shape.get('bpmnElement')
            if bpmn_element and bpmn_element.startswith('Participant_'):
                participant_id = bpmn_element
                break
        
        # If no participant found, generate one
        if participant_id is None:
            participant_id = 'Participant_01'
        
        # Check if collaboration already exists
        existing_collaboration = root.find('.//bpmn:collaboration', namespaces)
        if existing_collaboration is not None:
            print("Collaboration element already exists. Skipping creation.")
        else:
            # Create collaboration element with detected namespace
            collaboration = ET.Element('{%s}collaboration' % bpmn_ns)
            collaboration.set('id', plane_bpmn_element)
            
            # Create participant element
            participant = ET.SubElement(collaboration, '{%s}participant' % bpmn_ns)
            participant.set('id', participant_id)
            participant.set('name', process_name)
            participant.set('processRef', process_id)
            
            # Insert collaboration before process
            process_index = list(root).index(process)
            root.insert(process_index, collaboration)
        
        # Find all lane shapes to calculate participant shape dimensions
        lane_shapes = root.findall('.//bpmndi:BPMNShape[bpmndi:BPMNLabel]', namespaces)
        lanes = []
        
        for shape in root.findall('.//bpmndi:BPMNShape', namespaces):
            bounds = shape.find('dc:Bounds', namespaces)
            if bounds is not None:
                bpmn_element = shape.get('bpmnElement')
                # Check if this is a lane (has Lane_ prefix typically)
                if bpmn_element and 'Lane_' in bpmn_element:
                    x = float(bounds.get('x'))
                    y = float(bounds.get('y'))
                    width = float(bounds.get('width'))
                    height = float(bounds.get('height'))
                    lanes.append({'x': x, 'y': y, 'width': width, 'height': height})
        
        if lanes:
            # Calculate participant shape dimensions
            min_x = min(lane['x'] for lane in lanes)
            min_y = min(lane['y'] for lane in lanes)
            max_y = max(lane['y'] + lane['height'] for lane in lanes)
            first_lane_width = lanes[0]['width']
            
            participant_x = min_x - 60
            participant_y = min_y
            participant_width = first_lane_width + 60
            participant_height = max_y - min_y
            
            # Check if participant shape already exists
            participant_shape_exists = False
            for shape in root.findall('.//bpmndi:BPMNShape', namespaces):
                if shape.get('bpmnElement') == participant_id:
                    participant_shape_exists = True
                    # Update existing shape
                    bounds = shape.find('dc:Bounds', namespaces)
                    if bounds is not None:
                        bounds.set('x', str(int(participant_x)))
                        bounds.set('y', str(int(participant_y)))
                        bounds.set('width', str(int(participant_width)))
                        bounds.set('height', str(int(participant_height)))
                    break
            
            if not participant_shape_exists:
                # Create participant shape
                bpmn_plane = root.find('.//bpmndi:BPMNPlane', namespaces)
                if bpmn_plane is not None:
                    participant_shape = ET.Element('{http://www.omg.org/spec/BPMN/20100524/DI}BPMNShape')
                    participant_shape.set('id', f'{participant_id}_di')
                    participant_shape.set('bpmnElement', participant_id)
                    participant_shape.set('isHorizontal', 'true')
                    
                    bounds = ET.SubElement(participant_shape, '{http://www.omg.org/spec/DD/20100524/DC}Bounds')
                    bounds.set('x', str(int(participant_x)))
                    bounds.set('y', str(int(participant_y)))
                    bounds.set('width', str(int(participant_width)))
                    bounds.set('height', str(int(participant_height)))
                    
                    label = ET.SubElement(participant_shape, '{http://www.omg.org/spec/BPMN/20100524/DI}BPMNLabel')
                    
                    # Insert at the beginning of BPMNPlane
                    bpmn_plane.insert(0, participant_shape)
        
        # Write the modified XML to output file
        tree.write(output_file, encoding='UTF-8', xml_declaration=True)
        print(f"Successfully added collaboration element to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error processing BPMN file: {e}")
        return False



# # Example usage
# if __name__ == "__main__":

#     # add lane rectangle
#     input_file = "/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/lanes/lane_1.bpmn"
#     output_file = "/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/lanes/V2_customer_feedback_process_with_lanes_1.bpmn"

#     try:
#         add_lane_diagram(input_file, output_file)
#     except FileNotFoundError:
#         print(f"Error: File '{input_file}' not found")
#     except Exception as e:
#         print(f"Error processing file: {e}")




#     input_file = "/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/lanes/merged_process_with_flows.bpmn"
#     output_file = "/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/lanes/merged_process_with_collaboration.bpmn"
    
#     add_collaboration_to_bpmn(input_file, output_file)