# Tasks

Another component of hm is a task utility service. Basically, with minimal effort, creating a control center that lets users ship off jobs on independent nodes to deal with tasks.

## task.yaml

Like many task management toolkits, we can supply a simple language for doing mundane thing in a platform agnostic way and having multiple commands at the ready. For this kind of work, YAML is quite a fun tool.

```yaml
# A quick demo of the task.yaml "language" that could one day be

name: Task-Example

#
# Properties are used for variable expansion when running
# commands. See more about this below.
#
properties:

  # The local file where our repo exists
  repo_dir:
    windows: "{home}/repo"
    unix: "{homepath}/repo"

  # The base of our hosted repositories
  gitbase: "https://github.com/jdoerepos"


#
# Requirements to run this node
#
requires:
  - git          # A command required at the cli
  - py::requests # A python module that can be imported


#
# A function that can be used in multiple locations
# See more on the :command below
#
m__run_diagnostic(root, end_url):
  - ":python -f execute_diagnostics.py {root} {end_url}"
  - ":print Diagnostic executed!"


#
# Where we defined independent tasks of select types. This
# lets us handle things like cron work, requests for 
#
tasks:

  build-git-basic:

    #
    # Tell the root layer that this command should have commands
    # exposed to the http server for calling.
    #
    type: request

    help: |
      Run a standardized build based on a build_script.py being
      located on the root of a git repo

    parameters:
      - [ "name", "str", "The name of the item to build" ]
      - [ "--tag", "str", "Build a specific tag" ]

    # 
    # The real meat of the config is here. This is a command_list
    # that describes a functional routine using both native os commands
    # as well as an arsenal of plugin-style commands built into
    # hivemind.util
    #
    # Any time you see a command starting with ':' that's a known
    # command.
    #
    # Any time you see a {<variable>} you're seeing a, recursive, platform
    # aware exapsion occur pulling from both the environment as well as the
    # properties above.
    #
    commands:
      - ":set this_repo_location {repo_dir}/{name}"   # Set variables
      - if: "not file_exists('{this_repo_location}')" # Quick python
        then:
          - ":mkdir {this_repo_location}"    # Custom mkdir
          - ":cd {this_repo_location}"       # Custom cd with auto-push/pop
          - "git clone {gitbase}/{name}.get" # native git command
          - ":cd pop"                        # Pop back out of the last dir
      - ":cd {this_repo_location}"
      - if_param: "--tag"           # Specific if for optional args
        then:
          - "git fetch --all"
          - "git checkout {tag}"
      - ":python -f build_script.py"


  #
  # A cron task can also be quickly setup for fun and profit 
  #
  run-diagnostics:
    type: cron

    time: "@midnight"

    help: |
      Run a diagnostic on the machine and report it to our monitor db

    commands:
      - ":cd {repo_dir}/utils"
      - ":method run_diagnostic({}, {})"
```

# The TaskNode

For the node itself, the runtime sits nicely in a helper node.

```py
from hivemind.util import TaskNode

if __name__ == '__main__':
    node = TaskNode(config="task.yaml")
    node.run()
```

With that running, both tasks are up and, while the cron job waits until midnight to execute, the request task will alert the control layer to add an available task at a pretty rest endpoint. Something that will also be taking a bit of work to setup.

# The Root Frontend

Well, now that we've spelled out how to add request based jobs to our task nodes, we need a way of managing them and firing them off. This probably takes the form of a simple web interface via jinja or something of that sort. This is open ended and can be discuessed at length in the near future.

It would also be great to have health and statistic data from the various nodes pump through here (probably integrated with the backend). This way, we know what we're making more readily.


