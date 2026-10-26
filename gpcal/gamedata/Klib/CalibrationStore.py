"""Persist numeric driver calibration; never execute legacy shell files."""
import argparse
import json
import os
from pathlib import Path
import re
import time
from Klib.Hardware import parameters_directory

AXES=('axis_leftx','axis_lefty','axis_rightx','axis_righty')
TRIGGERS=('trigger_left','trigger_right')
KEYS=tuple(f'{axis}_{field}' for axis in AXES for field in ('antideadzone','deadzone','max','center','min'))+tuple(
    f'{trigger}_{field}' for trigger in TRIGGERS for field in ('antideadzone','deadzone','max'))


def state_file():
    return Path(os.environ.get('GPCAL_STATE_DIR','/var/lib/gpcal'))/'calibration.json'


def validate(values):
    if not isinstance(values,dict) or set(values)!=set(KEYS):
        raise ValueError('Calibration must contain all supported axis and trigger parameters')
    for key,value in values.items():
        if type(value) is not int or not -65535<=value<=65535:
            raise ValueError(f'Invalid calibration parameter: {key}')
    for control in AXES+TRIGGERS:
        maximum=values[control+'_max']
        if not 0<=values[control+'_antideadzone']<=values[control+'_deadzone']<maximum:
            raise ValueError(f'Invalid deadzone or range: {control}')
        if control in AXES and not values[control+'_min']<values[control+'_center']<maximum:
            raise ValueError(f'Invalid stick center: {control}')
    return values


def snapshot():
    directory=parameters_directory()
    return validate({key:int((directory/key).read_text()) for key in KEYS})


def save(values):
    validate(values)
    path=state_file(); path.parent.mkdir(parents=True,exist_ok=True)
    stage=path.with_suffix('.new')
    with stage.open('w') as stream:
        os.chmod(stage,0o600)
        json.dump({'driver':parameters_directory().parent.name,'parameters':values},stream,indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    stage.replace(path)
    return path


def import_legacy(path):
    values={}
    pattern=re.compile(r'^echo\s+(-?\d+)\s*>\s*(/sys/module/(?:rsinput|retroid)/parameters/[^\s]+)\s*$')
    for line in Path(path).read_text().splitlines():
        match=pattern.fullmatch(line.strip())
        if match and Path(match[2]).name in KEYS:
            key=Path(match[2]).name
            if key in values: raise ValueError(f'Duplicate legacy parameter: {key}')
            values[key]=int(match[1])
    return save(values)


def restore():
    path=state_file()
    if not path.exists():
        print('GPcal: no saved calibration; keeping driver defaults',flush=True)
        return
    data=json.loads(path.read_text()); values=validate(data['parameters'])
    deadline=time.monotonic()+30
    while not (parameters_directory()/'update_params').exists():
        if time.monotonic()>=deadline: raise RuntimeError('Calibration driver did not become ready')
        time.sleep(.25)
    directory=parameters_directory()
    if data['driver']!=directory.parent.name:
        raise ValueError('Saved calibration belongs to a different driver')
    previous=snapshot()
    try:
        for key,value in values.items(): (directory/key).write_text(str(value)+'\n')
        (directory/'update_params').write_text('1\n')
    except OSError:
        for key,value in previous.items(): (directory/key).write_text(str(value)+'\n')
        (directory/'update_params').write_text('1\n')
        raise
    print(f'GPcal: restored {len(values)} parameters from {path}',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=('restore','inspect','save','import-legacy'))
    parser.add_argument('path',nargs='?')
    args=parser.parse_args()
    if args.operation=='restore': restore()
    elif args.operation=='inspect': print(json.dumps(snapshot(),indent=2))
    elif args.operation=='save': print(save(snapshot()))
    elif args.path: print(import_legacy(args.path))
    else: parser.error('import-legacy requires a file path')


if __name__=='__main__': main()
