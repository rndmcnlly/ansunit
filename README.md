# ansunit

## Overview

**Ansunit** is a declarative unit testing framework for *answer set programming* (primarily using the tools from the [Potassco](http://potassco.sourceforge.net/) project). Test suite descriptions are defined in [YAML](http://www.yaml.org/) syntax, and they translate into the building blocks from Python's [unittest](https://docs.python.org/2/library/unittest.html) testing framework.

## Usage
Place `ansunit.py` somewhere in your Python path.
`python -m ansunit tests.yaml`	

## Concepts
A test suite specification is a nested object definition in which important key names start with the word `Test`. Basic test specifications may define a **program** (a body of AnsProlog code), solver **arguments** (passed on the command line), and define an **expectation** for the result of running the program (regarding its satisfiability). Complex test specifications may make use of reusable **modules** described in a **definitions** specification.

### Test Keywords
- `Test ...` defines a subtest
- `Program` defines a literal piece of code (childen override parents)
- `Expect` defines an outcome (`SAT`, `UNSAT`, or `OPTIMAL`)
- `Arguments` defines a list of string arguments
- `Definitions` defines a mapping from module names to definitions
- `Modules` defines a list of modules that will participate in the test

### Module Keywords
A module may be defined as...

- `some. inline. code.`
- `{filename: foo.lp}`
- `{reference: another_module}`
- `{group: [module_a, module_b]}`


## Syntax

This simple specification defines two basic tests in canonical form (all details defined at the leaves of the specification).

	Test a implies b:
		Program: |
			b :- a.
			a.
			:- not b.
		Expect: SAT
		
	Test b not implies a:
		Program: |
			b :- a.
			b.
			:- not a.
		Expect: UNSAT

This complex specification defines four test cases (three of which are grouped into a common suite). A `Definitions` section defines several modules with complex indirect references that are to be used later. In the second test (suite) several variations on a common test setup are defined concisely by means of inheriting details defined in the enclosing suite. Now shown, it is also possible to define all details including `Modules`, `Arguments`, and even `Program` at the top level for use by inheritance.

	Definitions:
	  foo: {filename: foo.lp}
	  bar: {filename: bar.lp}
	  both: {group: [instance, encoding]}
	  instance: {reference: bar}
	  inline: |
	    #const width = 3.
	    dim(1..width).
	    { p(X) } :- dim(X).
	
	
	Test twisted references:
	  Definitions:
	    encoding: {reference: foo}
	  Modules: both
	  Expect: SAT
	
	Test inline various:
	  Modules: inline
	  Expect: SAT
	
	  Test small:
	    Arguments: -c width=1 
	
	  Test medium:
	    Arguments: -c width=3 
	
	  Test large:
	    Arguments: -c width=5

## Command line arguments
Run `python -m ansunit --help` for more information.

## Credits
Created by Adam M. Smith (adam@adamsmith.as)