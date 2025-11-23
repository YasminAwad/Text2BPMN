import xml.etree.ElementTree as ET

def add_lane_diagram(xml_file_path, output_file_path=None):
    """
    Add lane diagram information to a BPMN XML file.
    
    Args:
        xml_file_path: Path to the input BPMN XML file
        output_file_path: Path to save the modified XML (if None, overwrites input)
    
    Returns:
        The modified XML tree
    """
    # Parse the XML file
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # Define namespaces
    namespaces = {
        'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        'dc': 'http://www.omg.org/spec/DD/20100524/DC',
        'di': 'http://www.omg.org/spec/DD/20100524/DI'
    }
    
    # Register namespaces to preserve prefixes
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)
    
    # Find all lanes in the process
    lanes = root.findall('.//bpmn:lane', namespaces)
    
    # Find the BPMNPlane element
    bpmn_plane = root.find('.//bpmndi:BPMNPlane', namespaces)
    
    if bpmn_plane is None:
        print("Warning: BPMNPlane not found in the document")
        return tree
    
    for lane in lanes:
        lane_id = lane.get('id')
        lane_name = lane.get('name', '')
        
        # Get all flowNodeRef elements (references to elements in the lane)
        flow_node_refs = lane.findall('bpmn:flowNodeRef', namespaces)
        
        if not flow_node_refs:
            print(f"Warning: Lane {lane_id} has no flow nodes")
            continue
        
        # Collect bounds of all elements in the lane
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for flow_node_ref in flow_node_refs:
            element_id = flow_node_ref.text
            
            # Find the corresponding shape in the diagram
            shape = bpmn_plane.find(f".//bpmndi:BPMNShape[@bpmnElement='{element_id}']", namespaces)
            
            if shape is not None:
                bounds = shape.find('dc:Bounds', namespaces)
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
            print(f"Warning: No valid bounds found for lane {lane_id}")
            continue
        
        # Calculate lane dimensions
        height_sum = max_y - min_y
        width_sum = max_x - min_x  # Fixed: was max_x - max_y
        
        lane_x = min_x - 60
        lane_y = min_y - 60
        lane_width = width_sum + 120
        lane_height = height_sum + 120
        
        # Check if lane shape already exists
        existing_shape = bpmn_plane.find(f".//bpmndi:BPMNShape[@bpmnElement='{lane_id}']", namespaces)
        
        if existing_shape is not None:
            # Update existing shape
            bounds = existing_shape.find('dc:Bounds', namespaces)
            if bounds is not None:
                bounds.set('x', str(lane_x))
                bounds.set('y', str(lane_y))
                bounds.set('width', str(lane_width))
                bounds.set('height', str(lane_height))
            print(f"Updated lane diagram for: {lane_id}")
        else:
            # Create new lane shape element
            lane_shape = ET.Element(f'{{{namespaces["bpmndi"]}}}BPMNShape')
            lane_shape.set('id', f'{lane_id}_di')
            lane_shape.set('bpmnElement', lane_id)
            lane_shape.set('isHorizontal', 'true')
            
            # Create bounds element
            bounds = ET.SubElement(lane_shape, f'{{{namespaces["dc"]}}}Bounds')
            bounds.set('x', str(lane_x))
            bounds.set('y', str(lane_y))
            bounds.set('width', str(lane_width))
            bounds.set('height', str(lane_height))
            
            # Create label element
            label = ET.SubElement(lane_shape, f'{{{namespaces["bpmndi"]}}}BPMNLabel')
            
            # Insert the lane shape at the beginning of BPMNPlane
            bpmn_plane.insert(0, lane_shape)
            
            print(f"Added lane diagram for: {lane_id} (x={lane_x}, y={lane_y}, width={lane_width}, height={lane_height})")
    
    # Save the modified XML
    if output_file_path is None:
        output_file_path = xml_file_path
    
    tree.write(output_file_path, encoding='UTF-8', xml_declaration=True)
    print(f"\nModified XML saved to: {output_file_path}")
    
    return tree


# Example usage
if __name__ == "__main__":
    # Example: Process the BPMN file
    input_file = "/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/lanes/lane_1.bpmn"
    output_file = "/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/lanes/customer_feedback_process_with_lanes_1.bpmn"
    
    try:
        add_lane_diagram(input_file, output_file)
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
    except Exception as e:
        print(f"Error processing file: {e}")