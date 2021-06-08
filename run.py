import json
import logging
import os
import subprocess
import sys

from argparse import ArgumentParser, Namespace
from datetime import datetime
from getpass import getuser
from multiprocessing import cpu_count
from shlex import split as shlex_split
from shutil import copy2 as copyfile


BASEDIR = os.path.dirname(os.path.realpath(__file__))


def run_wikipedia(args: Namespace, tools_versions: dict) -> None:
    if args.without_wikipedia:
        logging.info("SKIPPING to create CZ WIKIPEDIA KB from its resource...")
        return
    if args.lang != "cs":
        logging.info(
            "SKIPPING to create CZ WIKIPEDIA KB from its resource due to different language was selected..."
        )
        return

    logging.info("STARTING to create CZ WIKIPEDIA KB from its resources...")
    git_root = os.path.join(BASEDIR, "kb_resources", "kb_cs_wikipedia")
    add_tool_version(repo_dir=git_root, tools_versions=tools_versions)

    script = os.path.join(git_root, "start.sh")
    cmd = f"{script} -l {args.lang} -m {args.m} -d {args.wikipedia_dump} -I {args.wikipedia_indir}"
    if args.log:
        cmd += " --log"

    ps = subprocess.Popen(shlex_split(cmd))
    retcode = ps.wait()

    if retcode != 0:
        sys.exit("WIKIPEDIA KB creation failed (was terminated with code: {retcode}).")


def run_wikidata(args: Namespace, tools_versions: dict) -> None:
    if args.without_wikidata:
        logging.info("SKIPPING to create WIKIDATA KB from its resource...")
        return

    logging.info("STARTING to create WIKIDATA KB from its resources...")

    git_root = os.path.join(BASEDIR, "kb_resources", "kb_all_wikidata")
    add_tool_version(repo_dir=git_root, tools_versions=tools_versions)
    """
    script = os.path.join(git_root, "start.sh")
    cmd = f"{script} -l {args.lang} -m {args.m}"
    if args.log:
        cmd += " --log"
    
    ps = subprocess.Popen(shlex_split(cmd))
    retcode = ps.wait()
    
    if retcode != 0:
        sys.exit("WIKIDATA KB creation failed (was terminated with code: {retcode}).")
    """


def kb_merge(args: Namespace, resources_versions: dict, tools_versions: dict) -> str:
    logging.info("Merging multiple KB resources into one Generic KB...")
    add_tool_version(repo_dir=BASEDIR, tools_versions=tools_versions)

    os.makedirs(get_merged_kb_dir(args), exist_ok=True)
    version_kb_merged = f"{args.lang}_wp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    fpath_kb_merged = get_merged_kb_path(
        args=args, kb_file=get_merged_kb_fname(version_kb_merged)
    )

    # fake merge - copy Wikipedia KB only
    if not args.without_wikipedia:
        try:
            copyfile(get_kb_wpedia_path(), fpath_kb_merged)
        except FileNotFoundError:
            sys.exit("No WIKIPEDIA KB file was found.")
        kb_wpedia_version = get_kb_version(get_kb_wpedia_path())
        # Get only original dump version without unix timestamp of KB creation
        # (we need to get cs_20210301 from cs_20210301-1619732151)
        resources_versions["wikipedia"] = kb_wpedia_version.rsplit("-", 1)[0]

    burn_versions(
        kb_path=fpath_kb_merged,
        version_kb_merged=version_kb_merged,
        resources_versions=resources_versions,
        tools_versions=tools_versions,
    )


    return version_kb_merged


def kb_tools(args: Namespace, kb_path: str) -> None:
    kb_cleaner(args=args, kb_path=kb_path)


def kb_cleaner(args: Namespace, kb_path: str) -> None:
    if args.lang == "cs":
        logging.info("STARTING to cleaning/marking common aliases in merged KB...")
        git_root = os.path.join(BASEDIR, "tools", "kb_aliases_cleaner")

        script = os.path.join(git_root, "start.sh")
        # f_kb_out = os.path.join(get_merged_kb_dir(args), "KB_cleaned.tsv")
        cmd = f"{script} --input-file {kb_path} --output-file {kb_path}"
        if args.log:
            cmd += " --debug"

        ps = subprocess.Popen(shlex_split(cmd))
        retcode = ps.wait()

        if retcode != 0:
            sys.exit(f"KB cleaner failed (was terminated with code: {retcode}).")


def add_tool_version(repo_dir: str, tools_versions: dict) -> None:
    try:
        repo_name = (
            subprocess.check_output(
                "basename `git config --get remote.origin.url`",
                cwd=repo_dir,
                shell=True,
            )
            .decode()
            .strip()
            .rstrip(".git")
        )
    except subprocess.CalledProcessError as err:
        sys.exit(f"Version capture failed - probably not a git repository ({repo_dir})")
    tools_versions[repo_name] = (
        subprocess.check_output(shlex_split("git rev-parse --short HEAD"), cwd=repo_dir)
        .decode()
        .strip()
    )
    if (
        subprocess.check_output(shlex_split("git status --short"), cwd=repo_dir)
        .decode()
        .strip()
    ):
        tools_versions[repo_name] += "_dirty"


def burn_versions(
    kb_path: str, version_kb_merged: str, resources_versions: dict, tools_versions: dict
) -> None:
    with open(kb_path) as f:
        lines = f.readlines()

    lines[0] = f"VERSION={version_kb_merged}\n"
    lines.insert(1, f"{json.dumps(resources_versions)}\n")
    lines.insert(2, f"{json.dumps(tools_versions)}\n")
    lines.insert(3, "\n")

    with open(kb_path, mode="w") as f:
        f.writelines(lines)


def get_kb_wpedia_path() -> str:
    return os.path.join(BASEDIR, "kb_resources", "kb_cs_wikipedia", "outputs", "KB.tsv")


def get_kb_version(kb_path: str) -> str:
    with open(kb_path) as f:
        first_line = f.readline().strip()
    try:
        kb_version = first_line.split("=", 1)[1]
    except IndexError:
        sys.exit("KB ERROR: Bad format of KB version (first line of KB).")

    return kb_version


def get_merged_kb_dir(args: Namespace) -> str:
    return os.path.join(BASEDIR, "outputs", args.lang)


def get_merged_kb_fname(kb_version: str) -> str:
    return f"KB_{kb_version}.tsv"


def get_merged_kb_path(args: Namespace, kb_file="KB.tsv") -> str:
    return os.path.join(get_merged_kb_dir(args), kb_file)


def create_parser_common() -> ArgumentParser:
    parser = ArgumentParser(description="Create knowledgebase from multiple sources.")
    # REQUIRED arguments
    ap_required = parser.add_argument_group("REQUIRED arguments")
    ap_required.add_argument(
        "-l", "--lang", required=True, help="Language of data sources to process."
    )

    # COMMON arguments
    ap_common = parser.add_argument_group("COMMON arguments")
    ap_common.add_argument(
        "-m",
        type=int,
        default=cpu_count(),
        help="""Number of pool processes to parallelize entities processing (only for some tasks).
                    (default: %(default)s)""",
    )
    ap_common.add_argument(
        "-u",
        "--deploy",
        "--upload",
        type=str,
        action="store",
        nargs="?",
        const=getuser(),
        help="Upload (deploy) KB to webstorage via given login (default: current user (%(const)s)).",
    )
    ap_common.add_argument(
        "--deploy-dev",
        action="store_true",
        help="Development mode of deploy (upload to separate space to prevent forming a new production version of KB)",
    )
    ap_common.add_argument(
        "--log", action="store_true", help="Log each step in its own log file."
    )
    ap_common.add_argument(
        "--without-wikipedia",
        action="store_true",
        help="Create knowledgebase without data from Wikipedia.",
    )
    ap_common.add_argument(
        "--without-wikidata",
        action="store_true",
        help="Create knowledgebase without data from Wikidata.",
    )

    return parser


def parser_add_wikipedia(parser: ArgumentParser) -> None:
    # WIKIPEDIA arguments
    ap_wikipedia = parser.add_argument_group("WIKIPEDIA arguments")
    ap_wikipedia.add_argument(
        "--wikipedia-dump",
        type=str,
        default="latest",
        help="Version of dumps to process (default: %(default)s).",
    )
    ap_wikipedia.add_argument(
        "--wikipedia-indir",
        type=str,
        default="/mnt/minerva1/nlp/corpora/monolingual/czech/wikipedia/",
        help="""Input directory of wikipedia dump files, which will be used as inputs for KB creation purposes
                    (default: %(default)s).""",
    )


def parser_add_wikidata(parser: ArgumentParser) -> None:
    # WIKIDATA arguments
    ap_wikidata = parser.add_argument_group("WIKIDATA arguments")
    # ap_wikidata.add_argument(...)
    ...


def parser_add_kb_cleaner(parser: ArgumentParser) -> None:
    # KB CLEANER arguments
    ...


def main() -> None:
    resources_versions = dict()
    tools_versions = dict()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s]: %(message)s", level=logging.INFO
    )

    parser = create_parser_common()
    parser_add_wikipedia(parser=parser)
    parser_add_wikidata(parser=parser)
    parser_add_kb_cleaner(parser=parser)
    args = parser.parse_args()

    # Run each resource to create its own KB and then merge these multiple KBs into one merged KB
    run_wikipedia(args=args, tools_versions=tools_versions)
    run_wikidata(args=args, tools_versions=tools_versions)
    version_kb_merged = kb_merge(
        args=args, resources_versions=resources_versions, tools_versions=tools_versions
    )
    kb_merged_path = get_merged_kb_path(
        args=args, kb_file=get_merged_kb_fname(kb_version=version_kb_merged)
    )

    # Run KB cleaner
    kb_tools(args=args, kb_path=kb_merged_path)

    # TODO: delete this part after NER and other tools is adjusted to KB with resources and tools versions
    kb_without_versions_path = kb_merged_path.rsplit(".", 1)
    kb_without_versions_path[0] += "_without_versions"
    kb_without_versions_path = ".".join(kb_without_versions_path)
    with open(kb_merged_path, mode="r") as f:
        lines = f.readlines()
    lines.pop(3)
    lines.pop(2)
    lines.pop(1)
    with open(kb_without_versions_path, mode="w") as f:
        f.writelines(lines)

    if args.deploy:
        logging.info("Deploying final knowledgebase to distribution storage.")
        script = os.path.join(BASEDIR, "deploy.sh")
        cmd = f"{script} -u {args.deploy} -v {version_kb_merged}"
        if args.deploy_dev:
            cmd += " --dev"
        print(cmd)

        ps = subprocess.Popen(shlex_split(cmd))
        retcode = ps.wait()


if __name__ == "__main__":
    main()
