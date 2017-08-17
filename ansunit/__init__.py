#!/usr/bin/env python

"""ansunit.py: declarative unit testing for answer set programming"""

from __future__ import print_function

import argparse
import unittest
import subprocess
import operator
import yaml
import re

parser = argparse.ArgumentParser(description="AnsProlog unit testing")
parser.add_argument("suite", help="test suite in YAML syntax")
parser.add_argument("-c","--dump_canonical",action="store_true",help="dump test spec with all details pushed to leaves; exit")
parser.add_argument("-l","--dump_list",action="store_true",help="dump transformed test names with filter matching; exit")
parser.add_argument("-v","--verbosity", action="count", default=0)
parser.add_argument("-s","--solver", default="clingo",help="which solver to use (default: clingo)")
parser.add_argument("-o","--show_stdout",action="store_true")
parser.add_argument("-e","--show_stderr",action="store_true")
parser.add_argument("-x","--show_execution",action="store_true")
parser.add_argument("-m","--filter_match",type=str,nargs="*",default=[],help="only run tests matching this regex")
parser.add_argument("-n","--filter_nomatch",type=str,nargs="*",default=[],help="only run tests *not* matching this regex")
parser.add_argument("-a","--solver_args",type=str,nargs="*",default=[])

def ensure_list(v):
  if type(v) == list:
    return v
  else:
    return [v]

def reduce_contexts(parent, local):

  """Combine two test contexts into one.
  For value types of dict and list, the new context will aggregate the parent
  and local contexts. For other types, the value of the local context will
  replace the value of the parent (if any)."""

  context = {}

  for k,v in parent.items():
    if type(v) == dict:
      d = v.copy()
      d.update(local.get(k,{}))
      context[k] = d
    elif type(v) == list:
      context[k] = v + ensure_list(local.get(k,[]))
    else:
      context[k] = local.get(k,v)

  for k in set(local.keys()) - set(parent.keys()):
    context[k] = local[k]

  return context

def resolve_module(module, definitions):
  """Resolve (through indirections) the program contents of a module definition.
  The result is a list of program chunks."""

  assert module in definitions, "No definition for module '%s'" % module
  
  d = definitions[module]
  if type(d) == dict:
    if 'filename' in d:
      with open(d['filename']) as f:
        return [f.read().strip()]
    elif 'reference' in d:
      return resolve_module(d['reference'], definitions)
    elif 'group' in d:
      return sum([resolve_module(m,definitions) for m in d['group']],[])
    else:
      assert False
  else:
    assert type(d) == str
    return [d]

def canonicalize_spec(spec, parent_context):
  """Push all context declarations to the leaves of a nested test specification."""

  test_specs = {k:v for (k,v) in spec.items() if k.startswith("Test")}
  local_context = {k:v for (k,v) in spec.items() if not k.startswith("Test")}

  context = reduce_contexts(parent_context, local_context)

  if test_specs:
    return {k: canonicalize_spec(v, context) for (k,v) in test_specs.items()}
  else:
    program_chunks = sum([resolve_module(m,context['Definitions']) for m in context['Modules']],[]) + [context['Program']]
    test_spec = {
      'Arguments': context['Arguments'],
      'Program': "\n".join(program_chunks),
      'Expect': context['Expect'],
    }
    return test_spec

def flatten_spec(spec, prefix,joiner=" :: "):
  """Flatten a canonical specification with nesting into one without nesting.
  When building unique names, concatenate the given prefix to the local test
  name without the "Test " tag."""

  if any(filter(operator.methodcaller("startswith","Test"),spec.keys())):
    flat_spec = {}
    for (k,v) in spec.items():
      flat_spec.update(flatten_spec(v,prefix + joiner + k[5:]))
    return flat_spec 
  else:
    return {"Test "+prefix: spec}



class SolverTestCase(unittest.TestCase):

  def __init__(self, spec, args, description):
    self.spec = spec
    self.description = description
    self.args = args
    super(SolverTestCase,self).__init__()

  def __str__(self):
    return self.description

  def runTest(self):
    cmd = "%s %s %s" % (self.args.solver, ' '.join(self.args.solver_args), ' '.join(self.spec['Arguments']))
    if self.args.show_execution: print("EXECUTING: ",cmd)
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    (out, err) = proc.communicate(self.spec['Program'].encode('utf8'))
    if self.args.show_stderr: print(err)
    if self.args.show_stdout: print(out)
    if self.spec['Expect'] == 'SAT':
      self.assertIn(proc.returncode,[10,30],msg='Expected SAT')
    elif self.spec['Expect'] == 'UNSAT':
      self.assertEqual(proc.returncode,20,msg='Expected UNSAT')
    elif self.spec['Expect'] == 'OPTIMAL':
      self.assertEqual(proc.returncode,30,msg='Expected OPTIMAL')
    else:
      assert False

def main():
  args = parser.parse_args()

  filename = args.suite
  with open(filename) as f:
    spec = yaml.load(f)

  initial_context = {
      'Definitions': {},
      'Modules': [],
      'Arguments': [],
      'Program': '',
      'Expect': 'SAT',
  }

  spec = canonicalize_spec(spec, initial_context)

  if args.dump_canonical:
    print(yaml.dump(spec))
    return


  flat_spec = flatten_spec(spec,filename)

  matchers = [re.compile(m) for m in args.filter_match]
  nomatchers = [re.compile(n) for n in args.filter_nomatch]

  def selected(k):
      pos = all([m.search(k) for m in matchers])
      neg = any([n.search(k) for n in nomatchers])
      return all([m.search(k) for m in matchers]) \
          and not any([n.search(k) for n in nomatchers])

  if args.dump_list:
    print("\n".join([(" * " if selected(k) else " - ") + k for k in sorted(flat_spec.keys())]))
    return

  active_tests = filter(lambda t: selected(t[0]), sorted(flat_spec.items()))

  suite = unittest.TestSuite([SolverTestCase(v,args,k) for (k,v) in active_tests])

  runner = unittest.TextTestRunner(verbosity=args.verbosity)
  result = runner.run(suite)
  return not result.wasSuccessful()

if __name__ == "__main__":
  import sys
  sys.exit(main() or 0)
