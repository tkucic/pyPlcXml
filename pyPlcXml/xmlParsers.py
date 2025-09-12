import xml.etree.ElementTree as ET
from .helpers import ns, file_type

#----------------- TC6 v200 and v201 PARSER-----------------------------
def tc6Parse(pathToXml, tc6_version=file_type.tc6v201, ignoredNs=()):
    """Returns a data dictionary of format:
    {
        #Project information
        info : {
            companyName
			companyURL
			projectName
			projectVersion
			projectURL
            contactPerson
			contentDescription
			contentGenerated
        },
        namespaces : [
            global: {
                prgs : [],
                fbs : [],
                fcs : [],
                dts : [],
                vars : []
            },
            OtherNsName : {
                prgs : [],
                fbs : [],
                fcs : [],
                dts : [],
                vars : []
            }
        ]
        #Implementation not designed yet
        Configurations : [
            Resources : [
        ]
    }"""
    data = {}

    #Change namespaces to tc6_0200 or tc6_0201
    if tc6_version == file_type.tc6v201:
        ns['ns'] = r"http://www.plcopen.org/xml/tc6_0201"
    elif tc6_version == file_type.tc6v200:
        ns['ns'] = r"http://www.plcopen.org/xml/tc6_0200"
    else:
        return None

    #Get project information
    tree = ET.parse(pathToXml)
    root = tree.getroot()
    fileHeader = root.find('ns:fileHeader', ns)
    contentHeader = root.find('ns:contentHeader', ns)
    data['info'] = {
        'companyName' : contentHeader.get('organization'),
		'companyURL' : fileHeader.get('companyURL'),
		'projectName' : contentHeader.get('name'),
		'projectVersion' : contentHeader.get('version'),
		'projectURL' : '',
        'contentDescription' : fileHeader.get('contentDescription'),
        'contactPerson' : contentHeader.get('author'),
		'contentGenerated' : contentHeader.get('modificationDateTime'),
    }
    #Find the project description if attribute missing
    if data['info']['contentDescription'] == None:
        desc = contentHeader.find('ns:Comment', ns)
        if desc != None:
            data['info']['contentDescription'] = desc.text
        else:
            data['info']['contentDescription'] = ''
    
    #Remove new lines from the description to prevent breaking the markdown
    for invalidChar in ('\n', '  '):
        data['info']['contentDescription'] = data['info']['contentDescription'].replace(invalidChar, ' ')

    #Find global POUs and Data types
    gNsElement = root.find('ns:types', ns)
    gNsItem = {
        'name' : 'Global'
    }
    #Find all global programs, function blocks, classes and functions (POUs)
    gNsItem['prgs'] = []
    gNsItem['fbs'] = []
    gNsItem['fcs'] = []
    gNsItem['class'] = []

    for pou in gNsElement.find('ns:pous', ns).findall('ns:pou', ns):
        temp = _parseTc6POU(pou)
        if temp.get('type') == 'program':
            gNsItem['prgs'].append(temp)
        elif temp.get('type') == 'functionBlock':
            gNsItem['fbs'].append(temp)
        elif temp.get('type') == 'function':
            gNsItem['fcs'].append(temp)
        elif temp.get('type') == 'class':
            gNsItem['class'].append(temp)

    ## Get data types
    gNsItem['dts'] = [_parseTc6DT(dt) for dt in gNsElement.find('ns:dataTypes', ns).findall('ns:dataType', ns)]
    gNsItem['vars'] = []

    #Find other namespaces (dont exist in TC6)
    data['namespaces'] = [gNsItem]

    #Support for CODESYS elements in the instance node
    for config in root.findall('./ns:instances/ns:configurations/ns:configuration', ns):
        for app in config.findall('./ns:resource', ns):
            devNs = {
                'name' : config.get('name')
            }
            devNs['prgs'] = []
            devNs['fbs'] = []
            devNs['fcs'] = []
            devNs['class'] = []
            devNs['dts'] = []
            devNs['vars'] = []

            #Find all global programs, function blocks, classes and functions (POUs) located in addData
            for addData in app.findall('./ns:addData/ns:data', ns):
                dataId = addData.get('name').split('/')[-1]
                if dataId == 'datatype':
                    devNs['dts'].append(_parseTc6DT(addData.find('./ns:dataType', ns)))
                elif dataId == 'pou':
                    temp = _parseTc6POU(addData.find('./ns:pou', ns))
                    if temp.get('type') == 'program':
                        devNs['prgs'].append(temp)
                    elif temp.get('type') == 'functionBlock':
                        devNs['fbs'].append(temp)
                    elif temp.get('type') == 'function':
                        devNs['fcs'].append(temp)
                    elif temp.get('type') == 'class':
                        devNs['class'].append(temp)

            #Now we add this namepace to the namespaces array only if it has code or data types inside
            if (devNs['prgs'] or devNs['fbs'] or devNs['fcs'] or devNs['class'] or devNs['dts']) and devNs['name'] not in ignoredNs:
                data['namespaces'].append(devNs)

    return data

def _parseTc6POU(pouNode):
    """Returns a dictionary of format:
    {
        'name' : 'POU name',
        'type': 'PRG, FB, FC, Class',
        'if' : [
            {
                'name' : 'VAR_BLOCK',
                'attributes' : 'retain',
                'vars' : []
            }
        ],
        'description' : '',
        'code' : 'Main code',
        'actions' : [
            {
                'name' : 'actionName',
                'code' : 'actionCode'
            }
        ],
        'methods' : [
            'name' : 'POU name',
            'code' : 'Main code',
            'if' : [
                {
                    'name' : 'VAR_BLOCK',
                    'attributes' : 'retain',
                    'vars' : []
                }
            ],
        ]
    }"""
    data = {
    'name' : pouNode.get('name'),
    'type' : pouNode.get('pouType'),
    'description' : _extractTc6Docs(pouNode.find('./ns:interface/ns:documentation', ns))
    }

    f = lambda node, req, ns : list(node.find(req, ns)) if node.find(req, ns) != None else []
    if data.get('type') == 'function':
        data['returnType'] = _parseTc6VarType(pouNode.find('./ns:interface/ns:returnType', ns))[1]

    #Parameters and variables
    data['if'] = _parseTc6Interface(pouNode)

    #Get its code only if its structured text or instruction list (textual based language)
    data['code'] = _extractTc6Code(pouNode)

    #Get actions
    data['actions'] = []
    data['methods'] = []
    
    if data.get('type') in ('program', 'functionBlock', 'class'):
        for action in f(pouNode, 'ns:actions', ns):
            act = {
                'name' : action.get('name'),
                'code' : '' 
            }
            act['code'] = _extractTc6Code(action)
            data['actions'].append(act)

    
        #Support CODESYS methods. Puts them in actions, skips the interface.
        addDatas = pouNode.findall('./ns:addData/ns:data', ns)
        for addData in addDatas:
            methodNode = addData.find('./ns:Method', ns)
            if methodNode != None:
                method = {
                    'name' : methodNode.get('name'),
                    'code' : '',
                    'returnType' : '',
                    'description' : _extractTc6Docs(methodNode.find('./ns:interface/ns:documentation', ns))
                }
                if methodNode.find('./ns:interface/ns:returnType', ns) != None:
                    method['returnType'] = _parseTc6VarType(methodNode.find('./ns:interface/ns:returnType', ns))[1]

                method['code'] = _extractTc6Code(methodNode)
                method['if'] = _parseTc6Interface(methodNode)

                data['methods'].append(method)
        
    return data

def _parseTc6Interface(node):
    #Put interface in block depending on type
    data = []
    for block in list(node.find('./ns:interface', ns)):
        if block.tag.endswith('outputVars'):
            data.append(_parseTc6VarBlock(block, 'VAR_OUTPUT'))
            
        elif block.tag.endswith('inputVars'):
            data.append(_parseTc6VarBlock(block, 'VAR_INPUT'))

        elif block.tag.endswith('inOutVars'):
            data.append(_parseTc6VarBlock(block, 'VAR_IN_OUT'))

        elif block.tag.endswith('externalVars'):
            data.append(_parseTc6VarBlock(block, 'VAR_EXTERNAL'))

        elif block.tag.endswith('tempVars'):
            data.append(_parseTc6VarBlock(block, 'VAR_TEMP'))

        elif block.tag.endswith('accessVars'):
            data.append(_parseTc6VarBlock(block, 'VAR_ACCESS'))

        elif block.tag.endswith('globalVars'):
            data.append(_parseTc6VarBlock(block, 'VAR_GLOBAL'))
        
        elif block.tag.endswith('localVars'):
            data.append(_parseTc6VarBlock(block, 'VAR'))
    return data
    
def _parseTc6VarBlock(block, typ):
    """Assembles a block out of a variable node"""
    varBlock = {
        'name' : typ,
        'vars' : []
    }
    #Check for attribute
    for atr in ('constant', 'retain', 'nonretain', 'persistent', 'nopersistent'):
        if block.get(atr):
            varBlock['attribute'] = atr
            break
    else:
        varBlock['attribute'] = ''
    
    #Codesys flavor attribute
    #Each variable can have a codesys attribute, which makes the whole block have that attribute
    codesys_attributes = []
    for var in list(block):
        if var.find('./ns:addData/ns:data/ns:Attributes/ns:Attribute', ns) != None:
            atr = var.find('./ns:addData/ns:data/ns:Attributes/ns:Attribute', ns).get('Name')
            codesys_attributes.append(atr)
    
    if 'input_constant' in codesys_attributes:
        varBlock['attribute'] = 'constant'

    #Get members
    varBlock['vars'].extend([_parseTc6Var(var, varBlock['attribute']) for var in list(block)])
    
    return varBlock

def _parseTc6DT(dtNode):
    """Returns a dictionary of format:
    {
        'name' : 'data type name',
        'baseType' : 'enum/struct/etc',
        'components' : [
            {
                'name' : 'variable name',
                'type' : 'variable type: Simple, derived, enum, array',
                'attribute' : '',
                'initialValue' : 'variable initialization value',
                'description' : 'description of the value'
            }
        'description' : ''
        ]
    }"""
    dtSet = {
        'name' : dtNode.get('name'),
        'baseType' : dtNode[0][0].tag[37:],
        'initialValue' : '',
        'attribute' : '', 
        'description' : _extractTc6Docs(dtNode.find('./ns:documentation', ns))
        }
    dtSet['components'] = []

    baseType = dtSet.get('baseType')
    if baseType == 'enum':
        for cpt in dtNode.findall('./ns:baseType/ns:enum/ns:values/ns:value', ns):
            dtSet['components'].append({
                'name' : cpt.get('name'),
                'initialValue' : cpt.get('value', ''),
                'attribute' : '',
                'type' : 'enum',
                'description' : '' #Tc6, enum description not supported
            })

    elif baseType == 'struct':
        #If data type has variable components then this
        for cpt in dtNode.findall('./ns:baseType/ns:struct/ns:variable', ns):
            dtSet['components'].append(_parseTc6Var(cpt, ''))
    else:
        pass

    return dtSet

def _parseTc6VarType(node):
    """Parses type node and returns then name of the data type used
     in this variable. Returns a tuple"""

    #Check if type is derived (struct or enum)
    if node.find('ns:derived', ns) != None:
        #Simple get the name for derived
        return ('derived', node.find('ns:derived', ns).get('name'))
        
    #Check if type is pointer
    elif node.find('ns:pointer', ns) != None:
        ptr = node.find('ns:pointer', ns)

        #Find base type. Base type node is the same as type node
        return ('pointer', f"POINTER TO {_parseTc6VarType(ptr.find('ns:baseType', ns))[1]}")

    #Check if type is array
    elif node.find('ns:array', ns) != None:
        arr = node.find('ns:array', ns)

        #Find base type.
        baseType = _parseTc6VarType(arr.find('ns:baseType', ns))

        #Get dimensions
        dims = arr.findall('ns:dimension', ns)
        if len(dims) == 1:
            dim = f"[{dims[0].get('lower')}..{dims[0].get('upper')}]"
        elif len(dims) == 2:
            dim = f"[{dims[0].get('lower')}..{dims[0].get('upper')}, {dims[1].get('lower')}..{dims[1].get('upper')}]"
        else:
            dim = f"[{dims[0].get('lower')}..{dims[0].get('upper')}, {dims[1].get('lower')}..{dims[1].get('upper')}, {dims[2].get('lower')}..{dims[2].get('upper')}]"
        
        #Finally assemble the type of the array
        return ('array', f"ARRAY{dim} OF {baseType[1]}")

    else:
        #It can only be a elementary value
        typ = node[0].tag.replace(f"{{{ns.get('ns')}}}",'')
        if typ == 'string':
            lenght = node[0].get('length')
            typ = f"STRING[{lenght}]"
        return ('elem', typ)

def _parseTc6Var(var, attribute):
    """Returns a dictionary of format:
    {
        'name' : 'variable name',
        'type' : 'variable type: Simple, derived, enum, array',
        'attribute' : 'constant | retain | nonretain | persistent | nopersistent',
        'initialValue' : 'variable initialization value',
        'description' : 'description of the value'
    }"""
    name = var.get('name')

    #Get name of the variable type: derived/array/simpleValue/pointer
    typ = _parseTc6VarType(var.find('./ns:type', ns))

    #Check for initial value

    if var.find('./ns:initialValue', ns) != None:
        #if var is elementary or pointer type
        if typ[0] == 'elem' or typ[0] == 'pointer':
            initialValue = var.find('./ns:initialValue/ns:simpleValue', ns).get('value')
        
        #if var is derived (struct, enum)
        elif typ[0] == 'derived':
            #struct and enum initialization not supported as its too complex to parse
            initialValue = ''
        
        #if var is array
        elif typ[0] == 'array':
            initValNode = var.find('./ns:initialValue/ns:arrayValue', ns)

            #Only array initializatio of elementary values is supported as parsing structs is hard
            try:
                initialValue = [val.find('ns:simpleValue', ns).get('value') for val in initValNode.findall('ns:value', ns)]
                #this has turned into an array, which means all the values are are wrapped in ''
                #might be a problem when dealing with numbers
                
            except AttributeError:
                initialValue = ''
    else:
        initialValue = ''

    #Check for comment
    comment = _extractTc6Docs(var.find('ns:documentation', ns))

    return {'name' : name, 'type' : typ[1], 'attribute' : attribute, 'initialValue' : str(initialValue), 'description' : comment}

def _extractTc6Docs(node):
    """Searches for iec documentation in the documentation node and returns a comment in string format"""
    if node == None:
        return ""
    
    for child in node.iter():
        #Check if these tags match
        if child.tag in ('{http://www.w3.org/1999/xhtml}p', '{http://www.w3.org/1999/xhtml}xhtml'):
            return child.text
    
    return ''

def _extractTc6Code(node):
    """Searches for ST or IL code inside of a pou node and returns it in a string format"""
    for codeType in ['./ns:body/ns:ST', './ns:body/ns:IL']:
        codeNode = node.find(codeType, ns)
        if codeNode != None:
            for child in codeNode.iter():
                if child.tag in ('{http://www.w3.org/1999/xhtml}p', '{http://www.w3.org/1999/xhtml}xhtml', '{http://www.w3.org/1999/xhtml}div'):
                    code = child.text
                    if code != None:
                        return code

    return ''


#----------------- IEC 61131-10 PARSER-----------------------------
def iec61131_10Parse(pathToXml, ignoredNs=()):
    data = {}
    """Returns a data dictionary of format:
    {
        #Project information
        info : {
            companyName
			companyURL
			projectName
			projectVersion
			projectURL
            contactPerson
			contentDescription
			contentGenerated
        },
        namespaces : [
            global: {
                prgs : [],
                fbs : [],
                fcs : [],
                dts : [],
                vars : []
            },
            OtherNsName : {
                prgs : [],
                fbs : [],
                fcs : [],
                dts : [],
                vars : []
            }
        ]
        #Implementation not designed yet
        Configurations : [
            Resources : [
        ]
    }"""
    #Change namespaces to iec61131-10
    ns['ns'] = r"www.iec.ch/public/TC65SC65BWG7TF10"

    #Get project information
    tree = ET.parse(pathToXml)
    root = tree.getroot()
    fileHeader = root.find('ns:FileHeader', ns)
    contentHeader = root.find('ns:ContentHeader', ns)
    data['info'] = {
        'companyName' : fileHeader.get('companyName'),
		'companyURL' : fileHeader.get('companyURL'),
		'projectName' : contentHeader.get('name'),
		'projectVersion' : contentHeader.get('version'),
		'projectURL' : '',
        'contactPerson' : contentHeader.get('author'),
		'contentDescription' : fileHeader.get('contentDescription'),
		'contentGenerated' : contentHeader.get('modificationDateTime'),
    }

    #Find global POUs and Data types
    gNsElement = root.find('./ns:Types/ns:GlobalNamespace', ns)
    gNsItem = {
        'name' : 'Global'
    }
    
    #Find all global namespace programs (POUs)
    gNsItem['prgs'] = [_parseIecPRG(prg) for prg in gNsElement.findall('ns:Program', ns)]
    gNsItem['fbs'] = [_parseIecFB(fb) for fb in gNsElement.findall('ns:FunctionBlock', ns)]
    gNsItem['fcs'] = [_parseIecFC(fc) for fc in gNsElement.findall('ns:Function', ns)]
    gNsItem['class'] = [{} for _class in gNsElement.findall('ns:Class', ns)]

    #Find all global namespace data types
    gNsItem['dts'] = [_parseIecDT(dt) for dt in gNsElement.findall('ns:DataTypeDecl', ns)]

    #Find all global variables
    gNsItem['var'] = []

    data['namespaces'] = [gNsItem]

    #Find other namespaces
    for nameSpace in gNsElement.findall('ns:NamespaceDecl', ns):
        nsItem = {
            'name' : nameSpace.get('name')
        }
        #Find all namespace programs (POUs)
        nsItem['prgs'] = [_parseIecPRG(prg) for prg in nameSpace.findall('ns:Program', ns)]
        nsItem['fbs'] = [_parseIecFB(fb) for fb in nameSpace.findall('ns:FunctionBlock', ns)]
        nsItem['fcs'] = [_parseIecFC(fc) for fc in nameSpace.findall('ns:Function', ns)]
        nsItem['class'] = [{} for _class in nameSpace.findall('ns:Class', ns)]

        #Find all namespace data types
        nsItem['dts'] = [_parseIecDT(dt) for dt in nameSpace.findall('ns:DataTypeDecl', ns)]
        nsItem['var'] = []

        if nsItem['name'] not in ignoredNs:
            data['namespaces'].append(nsItem)

    return data

def _parseIecFB(pouNode):
    """Returns a dictionary of format:
    {
        'name' : 'POU name',
        'type': 'PRG, FB, FC, Class',
        'description' : '',
        'if' : [
            {
                'name' : 'VAR_BLOCK',
                'attributes' : 'retain',
                'vars' : []
            }
        ],
        'code' : 'Main code',
        'actions' : [
            {
                'name' : 'actionName',
                'code' : 'actionCode'
            }
        ]
    }"""
    data = {
        'name' : pouNode.get('name'),
        'type' : 'Function block',
        'description' : '',
        'code' : ''
    }

    #Get its code only if its structured text or instruction list (textual based language)
    body = pouNode.find('./ns:MainBody/ns:BodyContent', ns)
    if body.get(f"{{{ns.get('xsi')}}}type") in ('ST', 'IL'):
        data['code'] = body[0].text

    f = lambda node, req, ns : list(node.find(req, ns)) if node.find(req, ns) != None else []

    #Parameters and variables
    data['if'] = []

    #Put interface in block depending on type
    if pouNode.find('./ns:Parameters/ns:OutputVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_OUTPUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(pouNode, './ns:Parameters/ns:OutputVars', ns)]
              })
    if pouNode.find('./ns:Parameters/ns:InoutVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_IN_OUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(pouNode, './ns:Parameters/ns:InoutVars', ns)]
              })
    if pouNode.find('./ns:Parameters/ns:InputVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_INPUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(pouNode, './ns:Parameters/ns:InputVars', ns)]
              })
    if pouNode.find('ns:Vars', ns):
        data['if'].append(
            {
              'name' : 'VAR',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(pouNode, 'ns:Vars', ns)]
              })
    if pouNode.find('ns:TempVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_TEMP',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(pouNode, 'ns:TempVars', ns)]
              })
    if pouNode.find('ns:ExternalVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_EXTERNAL',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(pouNode, 'ns:ExternalVars', ns)]
              })

    data['actions'] = []
    for act in pouNode.findall('ns:Action',ns):
        action = {
            'name' : act.get('name'),
            'code' : ''
        }
        #Get its code only if its structured text or instruction list (textual based language)
        body = act.find('./ns:Body/ns:BodyContent', ns)
        if body.get(f"{{{ns.get('xsi')}}}type") in ('ST', 'IL'):
            action['code'] = body[0].text
        data['actions'].append(action)

    data['methods'] = []

    return data

def _parseIecFC(fcNode):
    """Returns a dictionary of format:
    { 
        'name' : 'POU name',
        'type': 'Function',
        'description' : '',
        'resultType' : 'Simple value,
        'code' : 'Main code',
        'docStrings' : '',
        'if' : [
            {
                'name' : 'VAR_BLOCK',
                'attributes' : 'retain',
                'vars' : []
            }
        ]
    }"""
    data = {
        'name' : fcNode.get('name'),
        'type' : 'Function',
        'description' : '',
        'ResultType' : fcNode.find('./ns:ResultType/ns:TypeName', ns).text,
        'code' : ''
    }

    #Get its code only if its structured text or instruction list (textual based language)
    body = fcNode.find('./ns:MainBody/ns:BodyContent', ns)
    if body.get(f"{{{ns.get('xsi')}}}type") in ('ST', 'IL'):
        data['code'] = body[0].text

    #Get its interface. IN, OUT, IN_OUT and VAR are in the same dict
    f = lambda node, req, ns : list(node.find(req, ns)) if node.find(req, ns) != None else []

    #Parameters and variables
    data['if'] = []

    #Put interface in block depending on type
    if fcNode.find('./ns:Parameters/ns:OutputVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_OUTPUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(fcNode, './ns:Parameters/ns:OutputVars', ns)]
              })
    if fcNode.find('./ns:Parameters/ns:InoutVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_IN_OUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(fcNode, './ns:Parameters/ns:InoutVars', ns)]
              })
    if fcNode.find('./ns:Parameters/ns:InputVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_INPUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(fcNode, './ns:Parameters/ns:InputVars', ns)]
              })
    if fcNode.find('ns:TempVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_TEMP',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(fcNode, 'ns:TempVars', ns)]
              })
    if fcNode.find('ns:ExternalVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_EXTERNAL',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(fcNode, 'ns:ExternalVars', ns)]
              })

    return data

def _parseIecPRG(prgNode):
    """Returns a dictionary that represents a PRG"""
    data = {
        'name' : prgNode.get('name'),
        'description' : '',
        'type' : 'PRG',
        'code' : ''
    }

    #Get its code only if its structured text or instruction list (textual based language)
    body = prgNode.find('./ns:MainBody/ns:BodyContent', ns)
    if body.get(f"{{{ns.get('xsi')}}}type") in ('ST', 'IL'):
        data['code'] = body[0].text

    #Get its interface. External and local variables are in the same dict
    f = lambda node, req, ns : list(node.find(req, ns)) if node.find(req, ns) != None else []

    #Parameters and variables
    data['if'] = []

    #Put interface in block depending on type
    if prgNode.find('./ns:Parameters/ns:OutputVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_OUTPUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(prgNode, './ns:Parameters/ns:OutputVars', ns)]
              })
    if prgNode.find('./ns:Parameters/ns:InoutVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_IN_OUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(prgNode, './ns:Parameters/ns:InoutVars', ns)]
              })
    if prgNode.find('./ns:Parameters/ns:InputVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_INPUT',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(prgNode, './ns:Parameters/ns:InputVars', ns)]
              })
    if prgNode.find('ns:Vars', ns):
        data['if'].append(
            {
              'name' : 'VAR',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(prgNode, 'ns:Vars', ns)]
              })
    if prgNode.find('ns:TempVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_TEMP',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(prgNode, 'ns:TempVars', ns)]
              })
    if prgNode.find('ns:ExternalVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_EXTERNAL',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(prgNode, 'ns:ExternalVars', ns)]
              })
    if prgNode.find('ns:GlobalVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_GLOBAL',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(prgNode, 'ns:GlobalVars', ns)]
              })
    if prgNode.find('ns:AccessVars', ns):
        data['if'].append(
            {
              'name' : 'VAR_ACCESS',
              'attribute' : '',
              'vars' : [_parseIecVar(var) for var in f(prgNode, 'ns:AccessVars', ns)]
              })
    
    data['actions'] = []
    for act in prgNode.findall('ns:Action',ns):
        action = {
            'name' : act.get('name'),
            'code' : ''
        }
        #Get its code only if its structured text or instruction list (textual based language)
        body = act.find('./ns:Body/ns:BodyContent', ns)
        if body.get(f"{{{ns.get('xsi')}}}type") in ('ST', 'IL'):
            action['code'] = body[0].text
        data['actions'].append(action)

    data['methods'] = []
    
    return data

def _parseIecVar(varNode):
    """Returns a dictionary of format:
    {
        'name' : 'variable name',
        'type' : 'variable type: Simple, derived, enum, array',
        'initialValue' : 'variable initialization value',
        'description' : 'description of the value'
    }"""
    data = {
        'name' : varNode.get('name'),
        'type' : varNode.find('./ns:Type/ns:TypeName', ns).text,
        'attribute' : '',
        'description' : ''
    }

    #Initial value, works only with simple value at the moment. can be SimpleValue, ArrayValue, StructValue
    initVal = varNode.find('./ns:InitialValue/ns:SimpleValue', ns)
    if initVal != None:
        data['initialValue'] = initVal.get('value')
    else:
        data['initialValue'] = ''
    #Docs
    if varNode.find('./ns:Documentation', ns) != None:
        data['description'] = varNode.find('./ns:Documentation', ns).text
    return data

def _parseIecDT(dtNode):
    """Returns a dictionary of format:
    {
        'name' : 'data type name',
        'baseType' : 'enum/struct/etc',
        'components' : [
            {
                'name' : 'variable name',
                'type' : 'variable type: Simple, derived, enum, array',
                'initialValue' : 'variable initialization value',
                'description' : 'description of the value'
            }
        ]
    }"""
    dtSet = {
        'name' : dtNode.get('name'),
        'baseType' : dtNode[0][0].tag[37:],
        'initialValue' : '',
        'description' : ''
        }
    dtSet['components'] = []

    if dtSet.get('baseType') == 'enum':
        for cpt in dtNode.findall('./ns:baseType/ns:enum/ns:values/ns:value', ns):
            dtSet['components'].append({
                'name' : cpt.get('name'),
                'initialValue' : cpt.get('value'),
                'attribute' : '',
                'type' : 'enum',
                'description' : ''
            })

    elif dtSet.get('baseType') == 'struct':
        #If data type has variable components then this
        for cpt in dtNode.findall('./ns:baseType/ns:struct/ns:variable', ns):
            dtSet['components'].append(_parseIecVar(cpt))
    else:
        pass

    return dtSet