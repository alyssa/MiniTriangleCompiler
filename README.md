MiniTriangleCompiler
====================

Compile Mini Triangle, a simple programming language, files to python bytecode

The flow of the program works like this:

* mini triangle source code is fed to Scanner
* Scanner spits out a list of tokens
* Parser verifies that the tokens are correct on a grammar level and spits out an ast tree
* CodeGen walks down the ast tree and build a list of python bytecode 
* write out bytecode to pyc file

I've provided mini triangle files for testing purposes. You can find these files under testFiles directory.

Run
========

    $ python codegen.py path_to_test_file

The output will be a pyc file. You can run the pyc file directly.

    $ python path_to_pyc_file
    
    
Example
========

    $ python codegen.py mtfiles/factorial.mt
    $ python mtfiles/factorial.pyc
	  Enter a number, and it will print the factorial of it
    

TODO
========

 * Add input prompts to test files
 * Add grammar to a grammar.txt file
