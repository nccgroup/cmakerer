# Copyright (c) NCC Group, 2018
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import argparse
import sys
import os
import string

cmake_template = b'''\
cmake_minimum_required(VERSION 3.9)
project(%s)

set(CMAKE_CXX_STANDARD 11)

include_directories(SYSTEM
  %s
)

include_directories(
  %s
)

add_executable(%s
  %s
)
'''

def parse_args():
  parser = argparse.ArgumentParser(
    description='Generates 3 (generally non-buildable) cmake files ' +
                'to support code indexing.'
  )
  parser.add_argument('-o', '--output', metavar='<path>', type=str,
                      default="./CMakeLists.txt",
                      help='Output path. Defaults to ./CMakeLists.txt')
  parser.add_argument('-x', '--exclude', metavar='<path>', type=str, nargs=1,
                      action='append', default=[],
                      help='Path to exclude (repatable). ' +
                           'These are relative to the search root and do ' +
                           'not resolve relative path sequences.')
  parser.add_argument('-!', '--filter', metavar='<segment>', type=str, nargs=1,
                      action='append', default=[],
                      help='Path segments to filter (repatable). ' +
                           'These are used to exclude any path containing a ' +
                           'matching segment (e.g. `-! test` will exlude ' +
                           '`foo/bar/test/**`).')
  parser.add_argument('-s', '--source-types', metavar='<types,list>', type=str,
                      nargs=1, action='append', default=[],
                      help='Comma-delimited list of source file extensions ' +
                           'to search for. This overrides the defaults.')
  parser.add_argument('-i', '--header-types', metavar='<types,list>', type=str,
                      nargs=1, action='append', default=[],
                      help='Comma-delimited list of header file extensions ' +
                           'to search for. This overrides the defaults.')
  parser.add_argument('-z', '--exclude-cmake', action='store_true',
                      help='Shortcut for excluding typical cmake paths ' +
                           '(CMakeFiles, cmake).')
  parser.add_argument('-d', '--debug', action='store_true',
                      help='Debug output.')
  parser.add_argument('search_root', metavar='<root>', type=str,
                      help='Directory to search.')
  return parser.parse_args()

def is_excluded(dirpath, excludelst):
  for ex in excludelst:
    if dirpath == ex:
      return True
  return False

def is_filtered(dirname, filterlst):
  if dirname.startswith('.'):
    return True
  for f in filterlst:
    if dirname.lower() == f.lower():
      return True
  return False

def has_ext(filename, exts):
  parts = filename.split(os.extsep)
  if len(parts) == 0:
    return False
  return parts[-1] in exts

def main():
  args = parse_args()

  if args.search_root.endswith('/') or \
     args.search_root.endswith('\\'):
    args.search_root = args.search_root[:-1]

  excludelst = []
  for ex in args.exclude:
    e = ex[0]
    if len(e) < 1:
      continue
    if e[-1] in [os.sep,os.altsep]:
      excludelst.append(e[:-1])
    else:
      excludelst.append(e)
  if args.exclude_cmake:
    excludelst += ['CMakeFiles', 'cmake']

  filterlst = [f[0] for f in args.filter]


  code_exts = set(['c', 'h', 'cc', 'cpp', 'hpp', 'hh'])
  if len(args.source_types) != 0:
    st = ','.join(args.source_types).replace(' ','')
    code_exts = set(st.split(','))

  header_exts = set(['h', 'hpp', 'hh'])
  if len(args.header_types) != 0:
    ht = ','.join(args.header_types).replace(' ','')
    header_exts = set(ht.split(','))

  cwd = None
  try:
    cwd = os.getcwd()
    os.chdir(args.search_root)
  except OSError as e:
    sys.stderr.write("{}\n".format(e))
    sys.exit(1)

  srcfilelst = []
  includelst = set([])
  systemlst = set([])

  for root, dirs, files in os.walk('.', topdown=True):
    dirs[:] = [
      d
      for d in dirs
      if not (
        is_filtered(d, filterlst) or
        is_excluded(root[2:] + os.sep + d, excludelst)
      )
    ]

    for f in files:
      if has_ext(f, code_exts):
        srcfilelst.append((root[2:] + os.sep + f).replace('\\', '/'))
        if has_ext(f, header_exts):
          includelst.add(root[2:].replace('\\', '/').encode())

  cneedle = b'#include'
  needle = b'include'

  tab = bytes(range(256))
  d = string.whitespace.encode()
  for srcfile in srcfilelst:
    try:
      with open(srcfile, 'rb') as fd:
        contents = fd.read()
        lines = contents.split(b'\n')
        for line in lines:
          if needle not in line:
            continue
          cramped = line.translate(tab, delete=d)
          if not cramped.startswith(cneedle):
            continue
          rem = line[line.find(needle)+len(needle):].strip()
          if len(rem) == 0:
            continue
          quote = False
          system = False
          if rem[0] == b'"'[0]:
            quote = True
          elif rem[0] == b'<'[0]:
            system = True
          else:
            continue
          rem = rem[1:]
          pos = -1
          if quote:
            pos = rem.find(b'"')
          elif system:
            pos = rem.find(b'>')
          if pos == -1:
            continue
          inc = rem[:pos]
          if args.debug:
            if quote:
              print(b'found #include "%s"' % inc)
            elif system:
              print(b'found #include <%s>' % inc)
          if b'/' not in inc:
            if system:
              m = b'/' + inc
              for src in srcfilelst:
                s = src.encode()
                if s.endswith(m):
                  rpos = s.find(m)
                  s = s[:rpos]
                  if args.debug:
                    print(b'adding system include of %s for #include <%s>'
                          % (s, inc))
                  systemlst.add(s)
            continue

          incpath = b'/'.join(inc.split(b'/')[:-1])
          npaths = set([])
          lst = None
          if quote:
            lst = includelst
          elif system:
            lst = systemlst

          for path in lst:
            #path = path.encode()
            if path.endswith(b'/' + incpath):
              npath = path[:len(path)-len(b'/' + incpath)]
              npaths.add(npath)
          for npath in npaths:
            if args.debug:
              if quote:
                print(b'adding include of %s for #include "%s"'
                      % (npath, inc))
              elif system:
                print(b'adding system include of %s for #include <%s>'
                      % (npath, inc))
            lst.add(npath)
    except Exception as e:
      sys.stderr.write("{}: {}\n".format(srcfile, e))
      raise e

  projname = args.search_root.split('/')[-1].split('\\')[-1].encode()
  systemlst = [b'"' + inc + b'"' for inc in systemlst]
  systemlst.sort()
  systemstr = b'\n  '.join(systemlst)
  includelst = [b'"' + inc + b'"' for inc in includelst]
  includelst.sort()
  includestr = b'\n  '.join(includelst)
  srcfilelst = ['"' + src + '"' for src in srcfilelst]
  srcfilelst.sort()
  srcfilestr = '\n  '.join(srcfilelst).encode()

  output = cmake_template % (projname, systemstr, includestr,
                           projname, srcfilestr)


  if args.output == '-':
    sys.stdout.buffer.write(output)
  else:
    try:
      os.chdir(cwd)
    except OSError as e:
      sys.stderr.write("{}\n".format(e))
      sys.exit(1)
    with open(args.output, 'wb') as fd:
      fd.write(output)


if __name__ == '__main__':
  main()

__all__ = ["parse_args", "main"]
