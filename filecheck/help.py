HELP_TEXT = """filecheck - A Python-native clone of LLVMs FileCheck tool
usage: filecheck FLAGS check-file

FLAGS:
--input-file <file>                 : Specify an input file, default is stdin (-)            
--check-prefix <prefix>             : Check line prefix (default is CHECK)
--strict-whitespace                 : Don't ignore indentation
--comment-prefixes <a>,<b>,<c>      : Ignore lines starting with these prefixes, even if
                                      they contain check lines (default RUN,COM)

ARGUMENTS:
check-file                          : The file from which the check lines are to be read

This tries to be as close a clone of LLVMs FileCheck as possible. We use it in xDSL
for our tests. If a feature is missing, or behaviour deviates from LLVMs FileCheck,
please file a bug at github.com/AntonLydike/filecheck.
"""
