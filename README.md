# pyPlcXml  

This package provides a way to interface with various exported PLC xml formats and project structures programmatically and to provide a common data format between PLC vendors.  

Supported file types are:

- Codesys tc6v200 and tc6v201

- B&R Automation studio 4

- IEC61131-10

- preprocessed output of the pyPlcXml (json.dumps)

pyPlcXml returns a dictionary, representing the underlying data. Then the data can be used in any way available to imagination.

At the moment, only Structured text and Instruction list is available to be parsed.

## Notes

This project is still in development so help is appreciated. Not all features and data available to the parser is parsed.
Project doesn't own any PLC Open Xml standard documents, all code parsing was reverse engineered from the available data on the internet and the community data provided for testing of the parser.
Project doesn't have any links to plcopen.org but it is using data publicly available from plcopen.org.

## Available functions

``` python
    def parse(*args, **kwargs):
        """args[0] - path to file
            kwargs
                ignoredNs : list() - list of strings of namespaces to ignore"""
    
    def validate(pathToXml):
        """Validates a given file and returns a string if file is matching one of the supported formats.
        Supported formats: IEC61131_10_Ed1_0.xsd, tc6_xml_v201.xsd, tc6_xml_v200.xsd, .json preparsed data, .apj - B&R automation studio project
        If file doesnt match any, the function returns None"""
```

## Usage

```python
    >> fmt = pyPlcXml.validate(r'example_data\ia_tools_testProject.xml')
    >> print(fmt)
    .. file_type.tc6v200

    >> data = pyPlcXml.parse(r'example_data\ia_tools_testProject.xml', ignoredNs = ())
    >> data['info']['projectName']
    .. ia_tools test project
```

## Contributing

We appreciate feedback and contribution to this repo! Before you get started, please see the following:

- [contribution guidelines](CONTRIBUTING.md)
- [code of conduct guidelines](CODE-OF-CONDUCT.md)
- [This repo's contribution guide](CONTRIBUTING.md)

## Support + Feedback

Include information on how to get support. Consider adding:

- Use [Issues](issues) for code-level support
- Use [Community]() for usage, questions, specific cases

## License

Published under the [MIT](LICENSE) license
