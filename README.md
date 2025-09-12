# pyPlcXml  

This package provides a way to interface with IEC6311-10 PLC xml format programmatically and to provide a common data format between PLC vendors.  

Supported file types are:
- Codesys tc6v200 and tc6v201
- B&R Automation studio 4
- IEC61131-10
- preprocessed output of the pyPlcXml (json.dumps)

pyPlcXml returns a dictionary, representing the underlying data. Then the data can be used in any way available to imagination.
