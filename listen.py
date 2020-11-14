import os
import threading
import socketserver
import secrets
import subprocess
import glob
import time
import shlex
import json
import random
import shutil
import timeit

class Handler(socketserver.StreamRequestHandler):
	def handle(self):
		secret = secrets.token_hex(16).encode('utf-8')+b"\n"
		self.wfile.write(secret)
		problem = self.rfile.readline().decode('utf-8').strip()
		tests = self.rfile.readline().decode('utf-8').strip()
		if tests not in ('tests', 'pretests'): return
		language = self.rfile.readline().decode('utf-8').strip()
		if language not in ('python', 'java', 'c++', 'pypy'): return
		filename = self.rfile.readline().decode('utf-8').strip()
		timelimit = self.rfile.readline().decode('utf-8').strip()
		mem = '512' if problem in os.environ.get('INCMEM', '').split(',') else '256'
		try: float(timelimit)
		except ValueError: return
		program = b''
		line = self.rfile.readline()
		while line != secret and line != secret+b'\n':
			if line == b'': return
			program += line
			line = self.rfile.readline()
		tmp = '/tmp/'+secret.decode('utf-8').strip()
		os.mkdir(tmp)
		if not os.path.abspath(os.path.join(tmp, filename)).startswith(tmp+'/'): return
		os.mkdir(os.path.join(tmp, 'chroot'))
		open(os.path.join(tmp, 'chroot', filename), 'wb').write(program)
		uid = str(random.randint(65536, 1000000))
		nsjail = ['nsjail', '-Mo', '-u', str(uid), '-g', str(uid), '-c', os.path.join(tmp, 'chroot'), '-t', timelimit, '--rlimit_as', 'inf' if language == 'java' else mem, '--rlimit_stack', 'inf' if language == 'java' else mem, '--rlimit_nproc', 'soft' if language == 'java' else '16', '--rlimit_fsize', '10',
		          '--iface_no_lo', '-R', '/bin', '-R', '/lib', '-R', '/lib64', '-R', '/usr/bin', '-R', '/usr/lib', '-R', '/usr/lib64', '-R', '/etc/', '-R', '/opt/pypy3', '-Q', '--']
		if language == 'python': command = ['/usr/bin/python', '-S', filename]
		elif language == 'pypy': command = ['/usr/bin/pypy3', '-S', filename]
		elif language == 'java':
			p = subprocess.run(['/usr/bin/javac', os.path.join(tmp, 'chroot', filename)], capture_output=True)
			if p.returncode == 1 and b' is public, should be declared in a file named ' in p.stderr:
				new_filename = p.stderr.split(b'\n')[0].split(b' ')[-1].decode('utf-8')
				shutil.move(os.path.join(tmp, 'chroot', filename), os.path.join(tmp, 'chroot', new_filename))
				filename = new_filename
				subprocess.run(['/usr/bin/javac', os.path.join(tmp, 'chroot', filename)], capture_output=True)
			command = ['/usr/bin/java', '-Xmx'+mem+'m', filename[:-5] if filename.endswith('.java') else filename]
		elif language == 'c++':
			subprocess.run(['/usr/bin/g++', '-std=c++17', '-O3', os.path.join(tmp, 'chroot', filename), '-o', os.path.splitext(os.path.join(tmp, 'chroot', filename))[0]])
			command = [os.path.splitext(filename)[0]]
		tests = sorted(filter(lambda t: not t.endswith('.a'), glob.glob(os.path.join('problems', problem, tests, '*'))), key=lambda a: int(a.split('/')[-1]))
		results = []
		for test in tests:
			result = {}
			interactor = os.path.isfile(os.path.join('problems', problem, 'interactor'))
			if interactor:
				try: os.remove(os.path.join(tmp, 'fifo'))
				except OSError: pass
				os.mkfifo(os.path.join(tmp, 'fifo'))
				start = time.time()
				p = subprocess.run(['/bin/bash', '-c', shlex.join(nsjail+command) + f' < {tmp}/fifo | tee {tmp}/stdout | ' + shlex.join([os.path.join('problems', problem, 'interactor'), test, tmp+'/out']) + f' > {tmp}/fifo 2>/dev/null; echo "${{PIPESTATUS[0]}}"'], capture_output=True)
				if time.time() - start > float(timelimit) and int(p.stdout) == 137: result['status'] = 'timeout'
				elif int(p.stdout) == 137: result['status'] = 'memoryout'
				elif int(p.stdout) != 0: result['status'] = 'error'
			else:
				with open(test, 'rb') as stdin, open(os.path.join(tmp, 'stdout'), 'wb') as stdout:
					timervars = {'p': {}, 'subprocess': subprocess, 'nsjail': nsjail, 'command': command, 'stdin': stdin, 'stdout': stdout}
					result['runtime'] = timeit.timeit('p["p"] = subprocess.run(nsjail+command, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE)', number=1, globals=timervars)
					p = timervars['p']['p']
					if result['runtime'] > float(timelimit) and p.returncode == 137: result['status'] = 'timeout'
					elif p.returncode == 137: result['status'] = 'memoryout'
					elif p.returncode != 0: result['status'] = 'error'
			if not result.get('status'):
				r = subprocess.run([os.path.join('problems', problem, 'checker'), test, os.path.join(tmp, 'out' if interactor else 'stdout'), test+'.a'], capture_output=True)
				result['status'] = 'correct' if r.returncode == 0 else 'incorrect'
			with open(os.path.join(tmp, 'stdout')) as stdout: result['stdout'] = stdout.read(1000000)
			result['stderr'] = p.stderr[:1000000].decode('utf-8')
			result['test_case'] = int(test.split('/')[-1])
			results.append(result)
		self.wfile.write(json.dumps(results).encode("utf-8")+b"\n")
		shutil.rmtree(tmp)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	allow_reuse_address = True

if __name__ == '__main__':
	with ThreadedTCPServer(('0.0.0.0', 1337), Handler) as server:
		server.serve_forever()
