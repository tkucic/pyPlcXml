import setuptools

with open("README.md", 'r') as fh:
  long_description = fh.read()

setuptools.setup(
  name = 'pyPlcXml',
  packages = setuptools.find_packages(),
  version = '0.0.4',
  license='None',
  description = 'Python library that can parse popular xml project files from vendors like Codesys',
  long_description=long_description,
  long_description_content_type='text/markdown',
  author = 'Toni Kucic',
  author_email = 'tkucic@gmail.com',
  url = 'https://github.com/tkucic/pyPlcXml',
  download_url = 'https://github.com/tkucic/pyPlcXml/archive/v_01.tar.gz',
  keywords = ['IEC61131-10', 'Industrial automation', 'PLC Xml', 'Codesys', 'Twincat'],
  install_requires=['lxml'],
  classifiers=[
    'Development Status :: 4 - Beta',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Quality tools',
    'License :: None :: None',
    'Programming Language :: Python :: 3'
  ],
  package_data={'pyPlcXml': [
    'schema\*.xsd']}
)