"""Execute the committed notebook in a fresh Python kernel and retain outputs."""
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'notebooks/01_data_analysis.ipynb'
    nb=nbformat.read(path,as_version=4)
    manager=KernelManager(kernel_name='python3')
    # Use the same interpreter/environment that launched this command.
    manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
    client=NotebookClient(nb,timeout=180,kernel_name='python3',km=manager,
        resources={'metadata':{'path':str(ROOT/'notebooks')}})
    client.execute()
    nbformat.write(nb,path)
    cells=[c for c in nb.cells if c.cell_type=='code']
    assert [c.execution_count for c in cells]==list(range(1,len(cells)+1))
    assert all(c.outputs for c in cells)
    assert not any(o.output_type=='error' for c in cells for o in c.outputs)
    print(f'Executed {len(cells)} code cells sequentially; all outputs retained.')

if __name__=='__main__':main()
