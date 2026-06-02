import subprocess
cmd = ['gemini.cmd', '-m', 'gemini-2.5-flash', '-y', '--skip-trust', '-p', '']
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=False)
prompt = """SYSTEM INSTRUCTION:
You are the DRAFT_CODER. Your job is to write the initial project code strictly based on the CEO's briefing. Output ALL required files using the following strict XML format for each file:
<file name="path/to/filename.ext">
... raw code here ...
</file>
For python backend code, use final_code.py as the filename.
TASK: Create a simple hello world flask app"""
stdout, stderr = p.communicate(input=prompt)
print('STDOUT:', repr(stdout))
print('STDERR:', repr(stderr))
