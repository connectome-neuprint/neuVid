import argparse
import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import report_version

def is_gpu_cluster(cluster):
    return cluster.startswith("gpu")

def make_blender_cmd(blender_exe, args, unused_args):
    neuVid_dir = os.path.dirname(os.path.realpath(__file__))
    neuVid_render_script = os.path.join(neuVid_dir, "render.py")
    blender_args = " ".join(unused_args)
    blender_cmd = f"{blender_exe} --background --python {neuVid_render_script} -- --threads {args.slots} {blender_args}"

    return blender_cmd

def time_stamp():
    d0 = str(datetime.datetime.now())
    d1 = d0.replace(" ", "_")
    d2 = d1.replace(":", "-")
    i = d2.index(".")
    d3 = d2[:i]
    return d3

def make_job_name(unused_args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputJson", "-ij", "-i", dest="input_json_file", required=True, help="path to the JSON file describing the input")
    args, _ = parser.parse_known_args(unused_args)
    job_name = os.path.splitext(os.path.basename(args.input_json_file))[0]
    return job_name

def make_log_file(args, unused_args):
    if args.log_file:
        return args.log_file
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputJson", "-ij", "-i", dest="input_json_file", required=True, help="path to the JSON file describing the input")
    args, _ = parser.parse_known_args(unused_args)
    log_file = os.path.splitext(args.input_json_file)[0] + "_log_" + time_stamp() + ".txt"
    log_file = os.path.abspath(log_file)
    return log_file

def check_blender_cmd_for_gpu(blender_cmd):
    if not "optix" in blender_cmd and not "cuda" in blender_cmd:
        print(f"\nWarning: a GPU cluster is specified but render.py has no --optix or --cuda argument\n")

if __name__ == "__main__":
    report_version()

    blender_exe = sys.argv[0]

    argv = sys.argv
    if "--" not in argv:
        argv = []
    else:
        argv = argv[argv.index("--") + 1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("-P", dest="payer", required=True, help="account paying for the cluster time")
    parser.set_defaults(cluster="gpu_rtx8000")
    parser.add_argument("--cluster", "-cl", help="cluster name (e.g., `--cluster gpu_rtx8000`)")
    parser.set_defaults(slots=32)
    parser.add_argument("--slots", "-n", dest="slots", type=int, help="slot count")
    parser.set_defaults(log_file=None)
    parser.add_argument("--log", "-l", dest="log_file", help="path to the file that logs the output of the bsub command")
    parser.set_defaults(sync=True)
    parser.add_argument("--async", "-as", dest="sync", action="store_false", help="run asynchronously")

    args, unused_args = parser.parse_known_args(argv)

    print(f"Using slot count: {args.slots}")
    print(f"Using cluster: {args.cluster}")

    blender_cmd = make_blender_cmd(blender_exe, args, unused_args)

    job_name = make_job_name(unused_args)
    print(f"Using job name: {job_name}")

    log_file = make_log_file(args, unused_args)
    print(f"Logging job output to: {log_file}")

    # `-P flyem` bills the job to FlyEM
    # `-J Dm15-03-n4` sets the job name to `Dm15-03-n4`
    # `-n 32` reserve 32 slots/cores on one of the nodes for the job
    # `-K` keeps `bsub` from returning until the job is complete, to allow elapsed time measurement
    cmd = f"bsub -P {args.payer} -n {args.slots} -J {job_name} -o {log_file}"
    if args.cluster:
        cmd += f" -q {args.cluster}"
        if is_gpu_cluster(args.cluster):
            cmd += ' -gpu "num=1"'
            check_blender_cmd_for_gpu(blender_cmd)
    if args.sync:
        cmd += " -K "
        print("Running synchronously (waiting for the job to complete)")
    cmd += f" '{blender_cmd}'"
    print(f"Using submission command: {cmd}")

    t0 = datetime.datetime.now()
    os.system(cmd)
    t1 = datetime.datetime.now()

    print(f"Submitted at {t0}")
    print(f"Finished at {t1}")
    print(f"Elapsed time {(t1 - t0)}")
