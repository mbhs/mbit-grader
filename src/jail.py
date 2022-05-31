import os
import subprocess
import tempfile
from time import time as cur_time
import re
import filecmp


def prep_jail(lang, prog, opts, f):
    compile_time = opts.get("compile_time", "15")
    compile_mem = opts.get("compile_mem", "256")
    if lang == "py":
        f.write(prog)
        f.flush()
        os.chmod(f.name, 0o444)
    elif lang == "cpp":
        os.chmod(f.name, 0o666)
        try:
            proc = subprocess.run(
                [
                    "/usr/bin/nsjail",
                    "-Q",
                    "--config",
                    "/jail-cfg/jail-cpp.cfg",
                    "-t",
                    compile_time,
                    "--rlimit_as",
                    compile_mem,
                    "--rlimit_stack",
                    compile_mem,
                    "-B",
                    f"{f.name}:/program",
                    "-x",
                    "/usr/bin/g++",
                    "--",
                    "/usr/bin/g++",
                    "-x",
                    "c++",
                    "-std=c++17",
                    "-Ofast",
                    "-march=native",
                    "-o",
                    "/program",
                    "-",
                ],
                input=prog,
                capture_output=True,
                timeout=int(compile_time),
            )
        except subprocess.TimeoutExpired:
            return {"type": "error", "msg": "compile timeout"}
        if proc.returncode != 0:
            return {
                "type": "error",
                "msg": "compile error",
                "stdout": proc.stdout.decode("latin1"),
                "stderr": proc.stderr.decode("latin1"),
            }
        os.chmod(f.name, 0o555)
        # close without deleting in order to not occupy file while running
        f.file.close()
    elif lang == "java":
        f.close()
        oldf = f
        f = tempfile.TemporaryDirectory()
        oldf.close = f.cleanup
        oldf.name = f.name
        with tempfile.NamedTemporaryFile() as s:
            s.write(
                re.sub(rb"public\s+class\s+\w+", b"public class Program", prog, count=1)
            )
            s.flush()
            os.chmod(s.name, 0o444)
            os.chmod(f.name, 0o777)
            try:
                proc = subprocess.run(
                    [
                        "/usr/bin/nsjail",
                        "-Q",
                        "--config",
                        "/jail-cfg/jail-java.cfg",
                        "-t",
                        compile_time,
                        "--rlimit_as",
                        "4096",
                        "--rlimit_stack",
                        compile_mem,
                        "-R",
                        f"{s.name}:/Program.java",
                        "-B",
                        f"{f.name}:/classes/",
                        "-x",
                        "/usr/bin/javac",
                        "--",
                        "/usr/bin/javac",
                        f"-J-Xmx{compile_mem}m",
                        "/Program.java",
                        "-d",
                        "/classes"
                    ],
                    input=prog,
                    capture_output=True,
                    timeout=int(compile_time),
                )
            except subprocess.TimeoutExpired:
                return {"type": "error", "msg": "compile timeout"}
            if proc.returncode != 0:
                return {
                    "type": "error",
                    "msg": "compile error",
                    "stdout": proc.stdout.decode("latin1"),
                    "stderr": proc.stderr.decode("latin1"),
                }
            s.close()
            os.chmod(f.name, 0o555)
    else:
        return {"type": "error", "msg": "unknown language"}
    return {"type": "success"}


def run_jail(lang, inp, opts, fname):
    ofile = tempfile.NamedTemporaryFile()
    efile = tempfile.NamedTemporaryFile()
    mem = opts.get("mem", "256")
    time = opts.get("time", "2")
    iargs = {"input": inp} if isinstance(inp, bytes) else {"stdin": inp}
    if lang == "py":
        try:
            start = cur_time()
            proc = subprocess.run(
                [
                    "/usr/bin/nsjail",
                    "-Q",
                    "--config",
                    "/jail-cfg/jail-py.cfg",
                    "-t",
                    time,
                    "--rlimit_as",
                    mem,
                    "--rlimit_stack",
                    mem,
                    "-R",
                    f"{fname}:/program",
                ],
                **iargs,
                stdout=ofile,
                stderr=efile,
                timeout=int(time),
            )
            duration = int((cur_time() - start) * 1000)
        except subprocess.TimeoutExpired:
            return {"type": "error", "stdout": ofile, "stderr": efile, "msg": "timeout"}
        if proc.returncode == 0:
            return {
                "type": "success",
                "stdout": ofile,
                "stderr": efile,
                "runtime": duration,
            }
        else:
            return {
                "type": "error",
                "stdout": ofile,
                "stderr": efile,
                "msg": "runtime error",
                "runtime": duration,
            }
    elif lang == "cpp":
        try:
            start = cur_time()
            proc = subprocess.run(
                [
                    "/usr/bin/nsjail",
                    "-Q",
                    "--config",
                    "/jail-cfg/jail-cpp.cfg",
                    "-t",
                    time,
                    "--rlimit_as",
                    mem,
                    "--rlimit_stack",
                    mem,
                    "-R",
                    f"{fname}:/program",
                ],
                **iargs,
                stdout=ofile,
                stderr=efile,
                timeout=int(time),
            )
            duration = int((cur_time() - start) * 1000)
        except subprocess.TimeoutExpired:
            return {"type": "error", "stdout": ofile, "stderr": efile, "msg": "timeout"}
        if proc.returncode == 0:
            return {
                "type": "success",
                "stdout": ofile,
                "stderr": efile,
                "runtime": duration,
            }
        else:
            return {
                "type": "error",
                "stdout": ofile,
                "stderr": efile,
                "msg": "runtime error",
                "runtime": duration,
            }
    elif lang == "java":
        try:
            start = cur_time()
            proc = subprocess.run(
                [
                    "/usr/bin/nsjail",
                    "-Q",
                    "--config",
                    "/jail-cfg/jail-java.cfg",
                    "-t",
                    time,
                    "--rlimit_as",
                    "4096",
                    "--rlimit_stack",
                    mem,
                    "-R",
                    f"{fname}:/classes/",
                    "-x",
                    "/usr/bin/java",
                    "--",
                    "/usr/bin/java",
                    "-cp",
                    "/classes/",
                    "-XX:ParallelGCThreads=1",
                    "-XX:ConcGCThreads=1",
                    "-Xlog:disable",
                    f"-Xmx{mem}m",
                    "Program",
                ],
                **iargs,
                stdout=ofile,
                stderr=efile,
                timeout=int(time),
            )
            duration = int((cur_time() - start) * 1000)
        except subprocess.TimeoutExpired:
            return {"type": "error", "stdout": ofile, "stderr": efile, "msg": "timeout"}
        if proc.returncode == 0:
            return {
                "type": "success",
                "stdout": ofile,
                "stderr": efile,
                "runtime": duration,
            }
        else:
            return {
                "type": "error",
                "stdout": ofile,
                "stderr": efile,
                "msg": "runtime error",
                "runtime": duration,
            }
    else:
        ofile.close()
        efile.close()
        return {"type": "error", "msg": "unknown language"}


def do_jail(lang, prog, opts, inp):
    with tempfile.NamedTemporaryFile() as f:
        p = prep_jail(lang, prog, opts, f)
        if p["type"] == "error":
            return p
        return run_jail(lang, inp, opts, f.name)


def run_one_test(lang, prepfile, opts, infile, outfile, verifier):
    r = run_jail(lang, open(infile, "rb"), opts, prepfile)
    try:
        r["stdout"].seek(-1, 1)
        if r["stdout"].read(1) != b"\n":
            with open(r["stdout"].name, "ab") as s:
                s.write(b"\n")
    except OSError:
        pass
    r["stdout"].seek(0)
    # return a preview of stdout
    stdout = r["stdout"].read(10000).decode("latin1")
    if r["stdout"].read(1):
        stdout += "\n ... [more output trimmed] ...\n"
    r["stderr"].seek(0)
    # return a preview of stderr
    stderr = r["stderr"].read(10000).decode("latin1")
    if r["stderr"].read(1):
        stderr += "\n ... [more output trimmed] ...\n"
    if r["type"] != "success":
        r["stdout"].close()
        r["stderr"].close()
        r["stdout"] = stdout
        r["stderr"] = stderr
        return r
    if verifier is not None:
        proc = subprocess.run(
            [verifier, infile, r["stdout"].name, outfile],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        if proc.returncode != 0:
            return {
                "type": "error",
                "msg": "incorrect output",
                "stdout": stdout,
                "stderr": stderr,
                "runtime": r["runtime"],
            }
    elif not filecmp.cmp(outfile, r["stdout"].name):
        return {
            "type": "error",
            "msg": "incorrect output",
            "stdout": stdout,
            "stderr": stderr,
            "runtime": r["runtime"],
        }
    r["stdout"].close()
    r["stderr"].close()
    return {
        "type": "success",
        "stdout": stdout,
        "stderr": stderr,
        "runtime": r["runtime"],
    }
