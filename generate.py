from pathlib import Path
import subprocess
import shutil
import sys
import os

if len(sys.argv) != 2:
	print('Package directory is required')
	sys.exit(1)
package = sys.argv[1]
problems = os.path.join(package, 'problems')
if not os.path.isdir(problems) or os.path.isdir('problems') and os.path.samefile(package, 'problems'):
	print('Invalid package directory')
	sys.exit(1)
for group in os.listdir(problems):
	try: Path('problems/' + group).mkdir(parents=True)
	except FileExistsError:
		print(group+' already exists')
		continue
	shutil.copytree(os.path.join(problems, group, 'tests'), os.path.join('problems', group, 'tests'))
	shutil.copytree(os.path.join(problems, group, 'pretests'), os.path.join('problems', group, 'pretests'))
	subprocess.run(['g++', os.path.join(problems, group, 'files/check.cpp'), '-o', os.path.join('problems', group, 'checker')])
	if os.path.isfile(os.path.join(problems, group, 'files/interactor.cpp')): subprocess.run(['g++', os.path.join(problems, group, 'files/interactor.cpp'), '-o', os.path.join('problems', group, 'interactor')])
	print(group)
