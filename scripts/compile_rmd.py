import subprocess
import sys
import os

rscript_paths = [
    r"C:\Program Files\R\R-4.4.0\bin\Rscript.exe",
    r"C:\Program Files\R\R-4.3.3\bin\Rscript.exe",
    r"C:\Program Files\R\R-4.4.1\bin\Rscript.exe"
]

rscript = None
for p in rscript_paths:
    if os.path.exists(p):
        rscript = p
        break

if not rscript:
    print("Rscript executable not found")
    sys.exit(1)

print(f"Using Rscript: {rscript}")
cmd = [rscript, "-e", "rmarkdown::render('Laporan_UAS_TToS_UII.Rmd')"]
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
if res.returncode == 0:
    print("\n[SUCCESS] PDF generated: Laporan_UAS_TToS_UII.pdf")
else:
    print("\n[ERROR] Compilation failed with return code:", res.returncode)
