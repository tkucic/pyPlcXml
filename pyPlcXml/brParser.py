from .helpers import ns

#Standard lib dependencies
import os, re, datetime
import xml.etree.ElementTree as ET

#Setup regex patterns
RX_VAR_IDENTS = (
    r'VAR_INPUT\s?(?P<Attribute>RETAIN)?(?P<Members>.*?)END_VAR',
    r'VAR_OUTPUT\s?(?P<Attribute>RETAIN)?(?P<Members>.*?)END_VAR',
    r'VAR_IN_OUT\s?(?P<Attribute>RETAIN)?(?P<Members>.*?)END_VAR',
    r'\bVAR\s(?P<Attribute>(RETAIN|CONSTANT))?(?P<Members>.*?)END_VAR'
)
RX_VAR_MEMBER = r'(\s*(?P<Name>.*?)\s*):(\s*(?P<Redund>{.*?})?\s*)((?P<Type>.*?)\s*)(;\s*|\s*:=\s*(?P<Initial>.*?)\s*;\s*)\s*((\(\*(?P<Desc1>.*?)\*\)\s*)?(\(\*(?P<Desc2>.*?)\*\)\s*)?(\(\*(?P<Desc3>.*?)\*\)\s*)?)'
RX_PRG_ST_CYCLIC = r'(PROGRAM _CYCLIC)(?P<Code>.*?)(END_PROGRAM)'
RX_PRG_ST_INIT = r'(PROGRAM _INIT)(?P<Code>.*?)(END_PROGRAM)'
RX_PRG_ST_EXIT = r'(PROGRAM _EXIT)(?P<Code>.*?)(END_PROGRAM)'
RX_POU_ST_IDENT = r"(FUNCTION_BLOCK|FUNCTION)\s+(?P<Name>(\w+|\w+_\w+_\w+))\s(?P<Code>.*?)(END_FUNCTION_BLOCK|END_FUNCTION)"
RX_PRG_C_CYCLIC = r'void\s+_CYCLIC\s+(.*?)\(.*?\)\s*{(?P<Code>.*)}'
RX_PRG_C_INIT = r'void\s+_INIT\s+(.*?)\(.*?\)\s*{(?P<Code>.*)}'
RX_PRG_C_EXIT = r'void\s+_EXIT\s+(.*?)\(.*?\)\s*{(?P<Code>.*)}'
RX_POU_C_IDENT = r'(?P<ReturnType>void)\s+(?P<Name>.*?)\s*?(?P<Parameters>\(.*?\))\s*{(?P<Code>.+?)}'
RX_FB_IDENT = r'({REDUND_(OK|ERROR)})?\s*FUNCTION_BLOCK\s+(?P<Name>.*?)\s+(?P<Interface>.*?)END_FUNCTION_BLOCK'
RX_FC_IDENT = r'({REDUND_(OK|ERROR)})?\s*\bFUNCTION\s+(?P<Name>.*?)\s*:\s*(?P<ReturnType>.*?)\s(?P<Interface>.*?)\bEND_FUNCTION'
RX_ACTION_IDENT = r'ACTION\s(?P<Name>.*?):(?P<Code>.*?)END_ACTION'
RX_ACTION_CANDIDATE = r'(?<!:=)\s(?P<ActionName>[A-Za-z0-9_]*);'
RX_TYP_IDENT = r'TYPE\s(?P<StructData>.*?)END_TYPE'
RX_ENUM_VAR = r'(\s*(?P<VarName>.*?)\s*)(:=\s*(?P<Initial>.*?)\s*?)?[,\s]*((\(\*(?P<Desc1>.*?)\*\)\s*?)?(\(\*(?P<Desc2>.*?)\*\)\s*?)?(\(\*(?P<Desc3>.*?)\*\)\s*?)?)\n'
RX_ENUM_IDENT = r'(\s*(?P<Name>.*?)\s*):(\s*\()((\(\*(?P<Desc1>.*?)\*\)\s*)?(\(\*(?P<Desc2>.*?)\*\)\s*)?(\(\*(?P<Desc3>.*?)\*\)\s*)?)(?P<Data>.*?)(\);|\)\s*?:=(\s*(?P<Initial>.*?)\s*);)'
RX_STRUCT_IDENT = r'(\s*(?P<Name>.*?)\s*):(\s*(?P<Redund>{.*?})\s*)?(\s*STRUCT\s*)((\(\*(?P<Desc1>.*?)\*\)\s*)?(\(\*(?P<Desc2>.*?)\*\)\s*)?(\(\*(?P<Desc3>.*?)\*\)\s*)?)(?P<Data>.*?)(END_STRUCT;)'
RX_STRUCT_START = r'\s*.*\s*:\s*({.*})?\s*(STRUCT)+'
RX_STRUCT_END = r'\s*END_STRUCT;'
RX_ENUM_START = r'(.*\s*:\s*?)$'
RX_ENUM_END = r'(\)\s*(:=)?.*;)$'

def brParse(rootPath, ignoredNs=()):

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
    }"""
    data = {}

    #Get project information
    tree = ET.parse(rootPath)
    root = tree.getroot()
    data['info'] = {
        'companyName' : '',
		'companyURL' : '',
		'projectName' : os.path.basename(rootPath).split('.')[0],
		'projectVersion' : root.get('Version', '1.0-0'),
		'projectURL' : '',
        'contactPerson' : '',
		'contentDescription' : root.get('Description', ''),
		'contentGenerated' : str(datetime.datetime.now())
    }

    #Load the global namespace
    data['namespaces'] = [_parsegNs(path=os.path.join(os.path.dirname(rootPath), 'Logical'), ignoredNs=[])]

    #Load the libraries with the valid names(coming from cfg)
    for root, _, files in os.walk(os.path.join(os.path.dirname(rootPath), 'Logical')):
        #Filter out all files except '.lby' and '.prg'
        files = [fi for fi in files if fi.endswith(('.lby', '.prg')) and fi.lower() != 'binary.lby']
        for file in files:
            filepath = os.path.join(root, file)
            dirName = os.path.basename(os.path.dirname(filepath))
            #Skip if the namespace is ignored or lby is binary
            if dirName not in ignoredNs and dirName not in ['IecCheck']:
                data['namespaces'].append(_parseNs(path=filepath))
    return data

def _parseNs(path):
    """
    This function parses every file under and around the .lby or .prg file and returns a list of lists holding dictionaries.
    0 - Function blocks
    1 - Functions
    2 - Data types
    3 - Constants
    """
    data = {
        'name': os.path.basename(os.path.dirname(path))
    }
    if path.endswith('.prg'):
        data['type'] = 'Program namespace'
    else:
        data['type'] = 'Library'

    #Determine paths to interesting files
    paths = {
        'root' : os.path.dirname(path),
        'lby'  : path,
        'prg'  : path
    }
    paths['fun'] = None
    paths['pkg'] = os.path.join(os.path.dirname(os.path.dirname(path)), 'Package.pkg')
    paths['varFiles'] = set()
    paths['typFiles'] = set()
    paths['codeFiles'] = set()
    for root, _, files in os.walk(paths.get('root')):
        for file in files:
            fpath = os.path.join(root, file)
            if os.path.splitext(os.path.basename(fpath))[1] == '.var':
                paths['varFiles'].add(fpath)
            elif os.path.splitext(os.path.basename(fpath))[1] in ['.st', '.ab', '.c']:
                paths['codeFiles'].add(fpath)
            elif os.path.splitext(os.path.basename(fpath))[1] == '.typ':
                paths['typFiles'].add(fpath)
            elif os.path.splitext(os.path.basename(fpath))[1] == '.fun':
                paths['fun'] = fpath

    #Load this libraries data
    #Get data from the upper level Package.pkg
    tree = ET.parse(paths['pkg'])
    root = tree.getroot()
    for obj in root.findall('./pkg:Objects/pkg:Object', ns):
        if obj.text == data.get('name'):
            data['language'] = obj.get('Language', '')
            data['description'] = obj.get('Description', '')
            break
    
    #Get version and dependencies
    if data.get('type') == 'Library':
        tree = ET.parse(paths['lby'])
        root = tree.getroot()
        data['version'] = root.get('Version', '1.0-0')
        data['dependencies'] = [dep.get('ObjectName') for dep in root.findall('./lib:Dependencies/lib:Dependency', ns)]
    else:
        data['version'] = '1.0-0'
        data['dependencies'] = []

    #Parse functions and function blocks from .fun file and assemble their source code
    if paths.get('fun') != None:
        data['fbs'], data['fcs'] = _parseFun(paths.get('fun'), paths.get('codeFiles'))
    else:
        data['fbs'], data['fcs'] = [], []

    #Programs apear only in program namespaces and not in libraries
    if data.get('type') == 'Program namespace':
        data['prgs'] = [_parsePrg(paths.get('prg'), paths.get('varFiles'), paths.get('codeFiles'))]
    else:
        data['prgs'] = []

    #Parse data types
    data['dts'] = _parseDts(paths.get('typFiles'))
    
    #Classes dont exist in a B&R project
    data['class']  = []

    return data

def _parsegNs(path, ignoredNs=()):
    """Parses the project and assembles all fbs, fcs, dts, class and prgs that are not located in the same folder as a lby file. Everything that is not in a library is considered as a global"""
    data = {
        'name': 'Global',
        'type':'Library',
        'fbs' : [],
        'fcs' : [],
        'class' : [],
        'prgs' : []
    }

    #Determine paths to interesting files
    #PRGS cannot be global in B&R
    #FUN cannot be global in B&R
    #Typ files that are not next to .lby or .prg files
    #Var files that are not next to a .prg or .lby
    paths = {
        'var' : [],
        'typ' : []
    }
    for root, _, files in os.walk(path):
        files = (fi for fi in files if fi.endswith('.var'))
        for file in files:
            filepath = os.path.join(root, file)
            lbyIecFiles = (fi for fi in os.listdir(os.path.dirname(filepath)) if fi.endswith('.lby') or fi.endswith('.prg'))
            if not lbyIecFiles:
                paths['var'].append(filepath)
    for root, _, files in os.walk(os.path.dirname(path)):
        files = (fi for fi in files if fi.endswith('.typ'))
        for file in files:
            filepath = os.path.join(root, file)
            lbyIecFiles = (fi for fi in os.listdir(os.path.dirname(filepath)) if fi.endswith('.lby') or fi.endswith('.prg'))
            if not lbyIecFiles:
                paths['typ'].append(filepath)

    #Load this libraries data
    #Get data from the upper level Package.pkg
    data['language'] = ''
    data['description'] = 'Global namespace'
    data['version'] = f"1.0-0"
    data['dependencies'] = []

    #Parse data types
    data['dts'] = _parseDts(paths.get('typ'))

    return data
    
def _parsePrg(path, varFiles, codeFiles):
    """
    This function parses the given .prg file and assembles the PRG POU in dictionary format.
    0 - Init cycle code
    1 - Cyclic code
    2 - Exit code
    3 - Array of actions
    4 - Local variable list of dicts
    5 - Local data types list
    """
    data = {
        'name': os.path.basename(os.path.dirname(path)),
        'type':'Program'
    }

    #Parse the interface
    #Program namespace only has variables 
    data['if'] = []
    for varFile in varFiles:
        with open(varFile, 'r') as f:
            data['if'].extend(_parseInterface(f.read()))

    #Find the source code of this program
    data['code'], data['actions'] = _findSourceCode(data.get('name'), data.get('type'), codeFiles)

    return data

def _findSourceCode(name, pou_type, codeFiles):
    """Goes through give code files '.ab', '.st', '.c' and returns a tuple holding
    the main source code of the pou and a list of actions"""

    mainCode = None
    actions = []
    if pou_type == 'Program':
        #Find cyclic, init and exit code
        for codeFile in codeFiles:
            with open(codeFile, 'r') as f:
                data = f.read()
                for rx in (RX_PRG_ST_CYCLIC, RX_PRG_ST_INIT, RX_PRG_ST_EXIT, RX_PRG_C_CYCLIC, RX_PRG_C_INIT, RX_PRG_C_EXIT):
                    match = re.search(rx, data, re.S)
                    if match:
                        if rx in (RX_PRG_ST_CYCLIC, RX_PRG_C_CYCLIC):
                            mainCode = match.group('Code')

                        elif rx in (RX_PRG_ST_INIT, RX_PRG_C_INIT):
                            actions.append({
                                'name' : 'Init',
                                'code' : match.group('Code')
                            })

                        elif rx in (RX_PRG_ST_EXIT, RX_PRG_C_EXIT):
                            actions.append({
                                'name' : 'Exit',
                                'code' : match.group('Code')
                            })
            if mainCode != None and len(actions) >= 2:
                break

    elif pou_type in ('Function block', 'Function'):
        #Find the main source code
        for codeFile in codeFiles:
            with open(codeFile, 'r') as f:
                data = f.read()

            if codeFile.endswith(('.st', '.ab')):
                #Find all pou implementations. In case there are multiple per file
                for pouBlock in re.finditer(RX_POU_ST_IDENT, data, re.S):
                    if pouBlock.group('Name') == name:
                        mainCode = pouBlock.group('Code')
                        break

            elif codeFile.endswith('.c'):
                #Find all pou implementations. In case there are multiple per file
                for pouBlock in re.finditer(RX_POU_C_IDENT, data, re.S):
                    if pouBlock.group('Name') == name:
                        mainCode = pouBlock.group('Code')
                        break
            if mainCode != None:
                break
    
    #Main code must exist at this point of the parse
    if mainCode == None:
        raise Exception
    
    #Find any actions that belong to this POU
    #First parse all actions to a temporary list
    actionIdents = []
    for codeFile in codeFiles:
        #Actions supported only or ST and AB
        if codeFile.endswith(('.st', '.ab')):
            with open(codeFile, 'r') as f:
                data = f.read()
                for actionData in re.finditer(RX_ACTION_IDENT, data, re.S):
                    action = {
                        'name' : actionData.group('Name'),
                        'code' : actionData.group('Code')
                    }
                    actionIdents.append(action)

    #If no actions found, return
    if not actionIdents:
        return mainCode, actions

    #Search through the main code of the pou and if action called matches the name of an action
    # append the action
    for actionCandidate in re.finditer(RX_ACTION_CANDIDATE, mainCode, re.S):
        for action in actionIdents:
            if actionCandidate.group('ActionName') == action.get('name'):
                actions.append(action)
    
    #Search through the actions to find other action calls. The new actions get added to the
    #end of the list so they get searched too. Recursive action calling is not allowed in IEC
    #but if someone does that, this program will maybe fail or create duplicated data
    for action in actions:
        for actionCandidate in re.finditer(RX_ACTION_CANDIDATE, action.get('code'), re.S):
            for actionSrc in actionIdents:
                if actionCandidate.group('ActionName') == actionSrc.get('name'):
                    actions.append(actionSrc)

    return mainCode, actions

def _parseInterface(interfaceData):
    """Parses a string and returns a list of dictionary representing var blocks:
    {
        'name' : VAR_BLOCK,
        'attribute' : retain,
        'vars' : []
    }"""
    blocks = []

    #B&R HAS ONLY VAR_INPUT, VAR_INPUT RETAIN, VAR_OUTPUT, VAR_OUTPUT RETAIN, VAR_IN_OUT, VAR CONSTANT, VAR RETAIN
    for varIdentRx in RX_VAR_IDENTS:
        #First find all VAR - END VAR blocks
        for var_block in re.finditer(varIdentRx, interfaceData, re.S):
            block = {
                'name' : '',
                'attribute' : var_block.group('Attribute') if var_block.group('Attribute') != None else '',
                'vars' : []
            }
            if varIdentRx.startswith('VAR_INPUT'):
                block['name'] = 'VAR_INPUT'
            elif varIdentRx.startswith('VAR_OUTPUT'):
                block['name'] = 'VAR_OUTPUT'
            elif varIdentRx.startswith('VAR_IN_OUT'):
                block['name'] = 'VAR_IN_OUT'
            elif varIdentRx.startswith(r'\bVAR'):
                block['name'] = 'VAR'
                
            #For each VAR - END_VAR block, parse all members
            for member in re.finditer(RX_VAR_MEMBER, var_block.group('Members')):
                var = {
                    'name' : member.group('Name'),
                    'type' : member.group('Type'),
                    'initialValue' : member.group('Initial') if member.group('Initial') != None else '',
                    'description' : member.group('Desc1') if member.group('Desc1') != None else '',
                    'attribute' : var_block.group('Attribute') if var_block.group('Attribute') != None else ''
                }
                block['vars'].append(var)
            blocks.append(block)
    return blocks

def _parseDts(typFiles):
    """Returns a list of data types(Structs) in dictionary format"""
    dts= []
    
    for file in typFiles:
        #Parse the file
        with open(file, 'r') as file:
            sourceCode = file.read()
        
        #Parse from all TYPE -> END_TYPE
        for typ in re.finditer(RX_TYP_IDENT, sourceCode, re.S):
            #Split text belonging to structs and enumerations to simplify code
            structLines = []
            enumLines = []
            inStruct = False
            inEnum = False
            for line in typ.group('StructData').splitlines():
                if re.match(RX_STRUCT_START, line):
                    inStruct = True
                    structLines.append(line)
                elif re.match(RX_STRUCT_END, line):
                    inStruct = False
                    structLines.append(line)
                elif inStruct:
                    structLines.append(line)

                if not inStruct:
                    if re.match(RX_ENUM_START, line):
                        inEnum = True
                        enumLines.append(line)
                    elif re.search(RX_ENUM_END, line, re.M):
                        inEnum = False
                        enumLines.append(line)
                    elif inEnum:
                        enumLines.append(line)
            enumTxt = '\n'.join(enumLines)
            structTxt = '\n'.join(structLines)

            #Parse from all STRUCT -> END_STRUCT
            for match in re.finditer(RX_STRUCT_IDENT, structTxt, re.S):
                dt = {}
                dt['baseType'] = 'struct'
                dt['name'] = match.group('Name')
                dt['redund'] = match.group('Redund')
                dt['description'] = match.group('Desc1') if match.group('Desc1') != None else ''
                dt['field1'] = match.group('Desc2') if match.group('Desc2') != None else ''
                dt['field2'] = match.group('Desc3') if match.group('Desc3') != None else ''
            
                dt['components'] = []
                for cpt in re.finditer(RX_VAR_MEMBER, match.group('Data'), re.S):
                    var = {}
                    var['name'] = cpt.group('Name')
                    var['type'] = cpt.group('Type')
                    var['attribute'] = cpt.group('Redund')
                    var['initialValue'] = cpt.group('Initial') if cpt.group('Initial') != None else ''
                    var['description'] = cpt.group('Desc1') if cpt.group('Desc1') != None else ''
                    var['field1'] = cpt.group('Desc2') if cpt.group('Desc2') != None else ''
                    var['field2'] = cpt.group('Desc3') if cpt.group('Desc3') != None else ''
                    dt['components'].append(var)
                dts.append(dt)
            #Parse from enumeration
            for match in re.finditer(RX_ENUM_IDENT, enumTxt, re.S):
                dt = {}
                dt['name'] = match.group('Name')
                dt['baseType'] = 'enumeration'
                dt['components'] = []
                dt['description'] = match.group('Desc1') if match.group('Desc1') != None else ''
                dt['field1'] = match.group('Desc2') if match.group('Desc2') != None else ''
                dt['field2'] = match.group('Desc3') if match.group('Desc3') != None else ''
                dt['initialValue'] = match.group('Initial') if match.group('Initial') != None else ''
                
                dt['components'] = []
                for cpt in re.finditer(RX_ENUM_VAR, match.group('Data'), re.S):
                    var = {}
                    var['name'] = cpt.group('VarName')
                    var['type'] = ''
                    var['attribute'] = ''
                    var['initialValue'] = cpt.group('Initial') if cpt.group('Initial') != None else ''
                    var['description'] = cpt.group('Desc1') if cpt.group('Desc1') != None else ''
                    var['field1'] = cpt.group('Desc2') if cpt.group('Desc2') != None else ''
                    var['field2'] = cpt.group('Desc3') if cpt.group('Desc3') != None else ''
                    dt['components'].append(var)
                dts.append(dt)        
    return dts

def _parseFun(funFilePath, codeFiles):
    """Returns a tuple with lists of function blocks and functions as dictionaries"""
    fbs = []
    fcs = []

    #Parse the file
    with open(funFilePath, 'r') as file:
        data = file.read()

    #Check if data has function blocks
    for fbBlock in re.finditer(RX_FB_IDENT, data, re.S):
        fbd = {
            'name' : fbBlock.group('Name'),
            'type' : 'Function block'
            }

        #Parse the interface
        fbd['if'] = _parseInterface(fbBlock.group('Interface'))

        #Find the source code of this function block
        fbd['code'], fbd['actions'] = _findSourceCode(fbd.get('name'), fbd.get('type'),  codeFiles)
        fbs.append(fbd)

    #Check if data has functions
    for fcBlock in re.finditer(RX_FC_IDENT, data, re.S):
        fcd = {
            'name' : fcBlock.group('Name'),
            'type' : 'Function',
            'returnType' : fcBlock.group('ReturnType')
        }
        
        #Parse the interface
        fcd['if'] = _parseInterface(fcBlock.group('Interface'))
        
        #Find the source code of this function
        fcd['code'], fcd['actions'] = _findSourceCode(fcd.get('name'), fcd.get('type'),  codeFiles)
        fcs.append(fcd)
    return fbs, fcs