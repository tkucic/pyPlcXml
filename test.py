import pyPlcXml, json, pstats, cProfile, os

def traverseProject(data):
    print('List contents')
    for ns in data['namespaces']:
        print('NAMESPACE: ', ns.get('name'), '-------------------------')
        print('\tPROGRAMS-------------------------')
        for prg in ns.get('prgs'):
            print('\t\t', prg.get('name'))
        print('\tFUNCTION BLOCKS-------------------------')
        for fb in ns.get('fbs'):
            print('\t\t', fb.get('name'))
        print('\tFUNCTIONS-------------------------')
        for fc in ns.get('fcs'):
            print('\t\t', fc.get('name'))
        print('\tDATA TYPES-------------------------')
        for dt in ns.get('dts'):
            print('\t\t', dt.get('name'))

def parseAllExamples():
    xmls = [
        ('TestData1', r'example_data\FiFoLib.xml'),
        ('TestData2', r'example_data\ia_tools_testProject.xml'),
        ('TestData3', r'example_data\IEC61131_10_Ed1_0_Example.xml'),
        ('TestData4', r'example_data\oscat_basic_331_codesys3.xml'),
        ('TestData5', r'example_data\oscat_building_100.xml'),
        ('TestData6', r'example_data\oscat_network_1352.xml'),
        ('TestData7', r'example_data\tc6_v200_Example1.xml'),
        ('TestData8', r'example_data\tc6_v200_Example2.xml'),
        ('TestData9', r'example_data\tc6_v200_Example3.xml'),
        ('TestData10', r'example_data\tc6_v200_Example4.xml'),
        ('TestData11', r'example_data\tc6_v200_Example5.xml'),
        ('TestData12', r'example_data\tc6_v200_Example6.xml'),
        ('TestData13', r'example_data\tc6_v201_Example1.xml'),
        ('TestData14', r'example_data\tc6_v201_Example2.xml'),
        ('TestData15', r'example_data\XML-Testproject-V201.xml')
    ]
    for ml in xmls:
        fmt = pyPlcXml.validate(ml[1])
        print('Format: ', fmt)

        print('Trying to parse: ', ml[1])
        data = pyPlcXml.parse(ml[1], ignoredNs = ())
        fpath= os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testOut', f'{ml[0]}_dataDump.json')
        
        traverseProject(data)
        
        print('Dumping json to: ', fpath)
        json.dump(data, open(fpath, 'w' ), indent=2)

if __name__ == '__main__':

    #Run the cProfiler on the tester function
    profileDumpFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testOut')
    with cProfile.Profile() as pr:
        parseAllExamples()
    pr.dump_stats(os.path.join(profileDumpFolder, 'parseProfile.profile'))
    with open(os.path.join(profileDumpFolder, 'parseProfile.txt'), "w") as f:
        ps = pstats.Stats(os.path.join(profileDumpFolder, 'parseProfile.profile'), stream=f)
        ps.sort_stats('cumulative')
        ps.print_stats()