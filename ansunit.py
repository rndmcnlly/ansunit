#!/usr/bin/env python

"""ansunit.py: declarative unit testing for answer set programming"""

import argparse
import unittest
import subprocess
import operator
import yaml
import re

parser = argparse.ArgumentParser(description="AnsProlog unit testing")
parser.add_argument("suite", help="test suite in YAML syntax")
parser.add_argument("-c","--dump_canonical",action="store_true")
parser.add_argument("-v","--verbosity", action="count", default=0)
parser.add_argument("-s","--solver", help="solver command", default="clingo")
parser.add_argument("-o","--show_stdout",action="store_true")
parser.add_argument("-e","--show_stderr",action="store_true")
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

  assert module in definitions
  
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

class SolverTestCase(unittest.TestCase):

  def __init__(self, spec, args, description):
    self.spec = spec
    self.description = description
    super(SolverTestCase,self).__init__()

  def __str__(self):
    return self.description

  def runTest(self):
    cmd = "%s %s %s" % (args.solver, ' '.join(args.solver_args), ' '.join(self.spec['Arguments']))
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    (out, err) = proc.communicate(self.spec['Program'])
    if args.show_stderr: print err
    if args.show_stdout: print out
    if self.spec['Expect'] == 'SAT':
      self.assertEqual(proc.returncode,10,msg='Expected SAT')
    elif self.spec['Expect'] == 'UNSAT':
      self.assertEqual(proc.returncode,20,msg='Expected UNSAT')
    elif self.spec['Expect'] == 'OPTIMAL':
      self.assertEqual(proc.returncode,30,msg='Expected OPTIMAL')
    else:
      assert False

def make_suite(spec,args,description):

  test_names = filter(operator.methodcaller('startswith','Test'),spec)

  if test_names:
    subtests = {t: make_suite(spec[t],args,description + ' :: ' + t[5:]) for t in test_names}
    return unittest.TestSuite(map(operator.itemgetter(1),sorted(subtests.items())))
  else:
    return SolverTestCase(spec,args,description)


if __name__ == "__main__":
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

  if args.dump_canonical: print yaml.dump(spec)

  suite = make_suite(spec,args,filename)

  unittest.TextTestRunner(verbosity=args.verbosity).run(suite)
