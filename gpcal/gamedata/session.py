"""Run calibration with access to the physical gamepad, restoring InputPlumber."""
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from Klib.CalibrationStore import import_legacy, state_file
from Klib.Hardware import open_gamepad


def main():
    root=Path(__file__).resolve().parent
    runtime=list((root/'pyxel'/'lib').glob('python*/site-packages'))
    if len(runtime)!=1: raise RuntimeError('Expected one packaged Pyxel runtime')
    with open('/run/lock/thorch-gpcal.lock','w') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise SystemExit('GPcal is already running')
        legacy=Path.home()/'.config/autostart/GPcal.sh'
        if not state_file().exists() and legacy.exists():
            print(f'GPcal: importing numeric calibration from {legacy}',flush=True)
            try: import_legacy(legacy)
            except (OSError,ValueError) as error:
                print(f'GPcal: legacy calibration was not imported: {error}',flush=True)
        active=subprocess.run(['systemctl','is-active','--quiet','inputplumber.service']).returncode==0
        child=None
        def interrupted(signum,frame):
            if child is not None and child.poll() is None: child.terminate()
            raise SystemExit(128+signum)
        for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP): signal.signal(signum,interrupted)
        try:
            if active:
                print('GPcal: temporarily stopping InputPlumber for physical calibration',flush=True)
                subprocess.run(['systemctl','stop','inputplumber.service'],check=True)
            deadline=time.monotonic()+10
            while True:
                try:
                    device,_=open_gamepad(); device.close(); break
                except (OSError,RuntimeError):
                    if time.monotonic()>=deadline: raise
                    time.sleep(.1)
            env=os.environ.copy()
            env['PYTHONPATH']=os.pathsep.join((str(runtime[0]),str(root)))
            env['PYTHONDONTWRITEBYTECODE']='1'
            child=subprocess.Popen([sys.executable,str(root/'main.py'),*sys.argv[1:]],cwd=root,env=env)
            return child.wait()
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.kill(); child.wait()
            if active:
                print('GPcal: restoring InputPlumber',flush=True)
                subprocess.run(['systemctl','start','inputplumber.service'],check=True)


if __name__=='__main__':
    raise SystemExit(main())
