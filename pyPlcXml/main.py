import pkg_resources, json, os
from lxml import etree
from .xmlParsers import tc6Parse, iec61131_10Parse
from .brParser import brParse
from .helpers import file_type

def parse(*args, **kwargs):
    """args[0] - path to file
        kwargs
            ignoredNs : list() - list of strings of namespaces to ignore"""
    match validate(args[0]):
        case file_type.bnr:
            return brParse(args[0], kwargs.get('ignoredNs', ()))
        case file_type.tc6v200:
            return tc6Parse(args[0], file_type.tc6v200, kwargs.get('ignoredNs', ()))
        case file_type.tc6v201:
            return tc6Parse(args[0], file_type.tc6v201, kwargs.get('ignoredNs', ()))
        case file_type.iec61131_10:
            return iec61131_10Parse(args[0], kwargs.get('ignoredNs', ()))
        case file_type.prepped:
            with open(args[0]) as f:
                return json.loads(f.read())
    return None
        
def validate(pathToXml):
    """Validates a given file and returns a string if file is matching one of the supported formats.
    Supported formats: IEC61131_10_Ed1_0.xsd, tc6_xml_v201.xsd, tc6_xml_v200.xsd, .json preparsed data, .apj - B&R automation studio project
    If file doesnt match any, the function returns None"""

    if pathToXml.endswith('.json'):
        return file_type.prepped
    elif pathToXml.endswith('.apj'):
        return file_type.bnr
    elif pathToXml.endswith('.xml'):
        for xmlSchema in ('IEC61131_10_Ed1_0.xsd', 'tc6_xml_v201.xsd', 'tc6_xml_v200.xsd'):
            schemaPath = pkg_resources.resource_filename(__name__, os.path.join('schema', xmlSchema))
            xmlschema_doc = etree.parse(schemaPath)
            xmlSchemaNode = etree.XMLSchema(xmlschema_doc)

            xml_doc = etree.parse(pathToXml)

            if xmlSchemaNode.validate(xml_doc):
                if xmlSchema == 'tc6_xml_v201.xsd':
                     return file_type.tc6v201
                if xmlSchema == 'tc6_xml_v200.xsd':
                     return file_type.tc6v200
                if xmlSchema == 'IEC61131_10_Ed1_0.xsd':
                     return file_type.iec61131_10
    return None