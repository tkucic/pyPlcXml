import re
from enum import Enum

#define constants
ns = {
    'pkg' : r"http://br-automation.co.at/AS/Package",
    'lib' : r"http://br-automation.co.at/AS/Library",
    'ns' : r"www.iec.ch/public/TC65SC65BWG7TF10",
    'xsi': r"http://www.w3.org/2001/XMLSchema-instance",
    'xhtml' : r"http://www.w3.org/1999/xhtml"
}

class file_type(Enum):
    tc6v201 = 1
    tc6v200 = 2
    iec61131_10 = 3
    bnr = 4
    prepped = 5

def _cleanLine(txt):
    unwanted = ('(***', '***)', '(* ', '(*', '*)','**')
    for thing in unwanted:
        txt = txt.replace(thing, "")
    return txt

def _extractDocStrings(code, docRx):
    matches = re.compile(docRx, flags=re.DOTALL).finditer(code)
    return [_cleanLine(match.group('DocString')) for match in matches]

def _findVar(var, text):
    """
    Takes in a regex variable name and searches for it in the text while ignoring case.\n
    Function returns a list containing line numbers of all found matches. Returns empty list if not found.\n
    Usage:\n
    Call the function with arguments passed:\n
    var = r'\\bvTonisVar'\n
    matchLoc = findVar(var, text)\n
    """
    results = re.findall(re.compile(fr'\b{var}', re.I), text)
    if results:
        return True
    return False

def _countLines(txt):
    '''Counts lines of code, comments not including empty lines and total lines'''
    splitLines = txt.splitlines()
    totalLines = len(splitLines)
    codeLines = totalLines
    commentLines = 0
    i = 0
    while i < totalLines:
        line = splitLines[i]
        trimmedLine = line.replace(' ', '').replace('\t', '')

        if trimmedLine == '':
            #Empty line
            codeLines -= 1
        elif trimmedLine.startswith('//'):
            #Single line comment
            commentLines += 1
            codeLines -= 1
        elif trimmedLine.startswith('(*'):
            #Single or multicomment
            if '*)' in trimmedLine:
                commentLines += 1
                codeLines -= 1
                i += 1
                continue
            #Find where the end of comment is
            comm_start = i
            i += 1
            while '*)' not in splitLines[i]:
                i += 1
            comm_end = i
            commentLines += (comm_end - comm_start + 1)
            codeLines -= (comm_end - comm_start + 1)
        i += 1
    return(codeLines, commentLines, totalLines)

def removeAddData(node):
    """Removes all nodes with addData tag"""
    for child in list(node):
        if child.tag == '{http://www.plcopen.org/xml/tc6_0200}addData':
            node.remove(child)
        else:
            removeAddData(child)
    return