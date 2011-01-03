##
## Author(s):
##  - Dimitri Merejkowsky <dmerejkowsky@aldebaran-robotics.com>
##  - Cedric GESTES <gestes@aldebaran-robotics.com>
##
## Copyright (C) 2009, 2010, 2011 Aldebaran Robotics
##

"Run the same command on each buildable projects"

import sys
import logging
import qitools

def usage():
    "Specific usage"
    return """\
foreach -- COMMAND

Example:
qibuild foreach -- cd build-sys-linux-x86_64 \; make clean all

Use -- to seprate qibuild arguments from the arguments of the command.
(The -- is mandatory)
"""

def configure_parser(parser):
    """Configure parser for this action """
    qitools.qiworktree.work_tree_parser(parser)
    parser.add_argument("command", metavar="COMMAND", nargs="+")
    parser.add_argument("--ignore-errors", action="store_true", help="continue on error")

def do(args):
    """Main entry point"""
    qiwt = qitools.qiworktree.open(args.work_tree, use_env=True)
    logger = logging.getLogger(__name__)
    for pname, ppath in qiwt.buildable_projects.iteritems():
        logger.info("Running `%s` for %s", " ".join(args.command), pname)
        try:
            qitools.command.check_call(args.command, cwd=ppath)
        except qitools.command.CommandFailedException, err:
            if args.ignore_errors:
                logger.error(str(err))
                continue
            else:
                raise

if __name__ == "__main__" :
    qitools.cmdparse.sub_command_main(sys.modules[__name__])

