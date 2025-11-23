from src.core.layout import BPMNLayoutService

with open("/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/valid_xml_2.bpmn", "r", encoding="utf-8") as f:
    bpmn_string = f.read()

service = BPMNLayoutService()
laid_out_xml = service.apply_layout(bpmn_string)

with open("/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/laid_out.bpmn", "w", encoding="utf-8") as f:
    f.write(laid_out_xml)