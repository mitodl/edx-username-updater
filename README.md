# edX Username Updater

This is a set of scripts that can help facilitate the changing of usernames in Open edX,
and in other apps that are set up to log into edX via SSO.

## Workflow

The workflow for using these scripts is generally as follows:
1. Clone this repo into a temporary directory on a machine running the app for which
  you want to update usernames (Open edX, xpro...).
1. Copy the files relevant to your app into the app's source directory.
1. Execute the desired script by piping an import command into a Django shell, e.g: 
  `echo "import <my_script>" | python ./manage.py shell`
  
This project includes a Makefile to take care of some of these steps.

## Setup

1. Navigate to the source directory of your app, e.g.: `/src`, `/edx/app/edxapp/edx-platform`
2. Clone this repo on the machine running your app.
    
    ```bash
    pushd .; cd /tmp && git clone https://github.com/mitodl/edx-username-updater.git; popd
    
    # If you want to use a branch other than master, make sure to check it out after cloning
    pushd .; cd /tmp/edx-username-updater && git fetch && git checkout -b <BRANCH_NAME> origin/<BRANCH_NAME>; popd
    ```
3. Set the `UPDATE_REPO_PATH` env var.
    
    ```bash
    # Change this value if you cloned the repo somewhere else
    export UPDATE_REPO_PATH=/tmp/edx-username-updater
    ```
4. Copy the relevant files to your source directory via `make` command.
    
    ```bash
    # If you're running this on an xPro machine...
    make -f $UPDATE_REPO_PATH/Makefile setup.xpro
    
    # If you're running this on an Open edX machine...
    make -f $UPDATE_REPO_PATH/Makefile setup.edx
    ```
5. Configure all of your apps with the same S3 credentials so they can all read/write
  files to the same location.

## Usage

Each one of these commands will write some JSON to stdout indicating the results
of the username change, and as long as S3 credentials are properly set, they will
also write a result file to S3. The result JSON written to stdout will indicate the
result file path if one was written. 

In practice, updates should first be performed in xpro to Django usernames, then in edX 
to Django usernames, then again in edX to forum usernames. The results from one step 
will indicate which usernames were successfully changed, and they will be used to apply
the same username updates in the next step.  

#### (Optional) Set path for result files

By default, the path to the result files directory for reading/writing is `.`.
This can be changed with the `RESULT_JSON_DIR_PATH` env var.

#### mitxpro – change Django User usernames

```bash
# To change all ulid-generated usernames...
make -f $UPDATE_REPO_PATH/Makefile run.xpro

# To regenerate usernames (based on full name or email) for specific users...
export USERNAMES_TO_REGENERATE="existing-username-1,existing-username-2"
make -f $UPDATE_REPO_PATH/Makefile run.xpro.specific
```

#### Open edX – change Django User usernames

```bash
# Change this value to match the file containing the results of the previous step
export XPRO_RESULT_JSON_FILENAME="xpro_username_changes_00000000_000000.json"
make -f $UPDATE_REPO_PATH/Makefile run.edx
```

#### Open edX – change forum usernames

```bash
# Change this value to match the file containing the results of the previous step
export EDX_RESULT_JSON_FILENAME="edx_username_changes_00000000_000000.json"
make -f $UPDATE_REPO_PATH/Makefile run.edx.forum
```

#### Rebuild the forum index

The discussion board/forum service also has an ES index to allow users to search for 
posts. The easiest way to update the usernames in those ES documents is to rebuild the 
index.

Run the following on a machine running the forum service ([command reference](https://github.com/edx/cs_comments_service/blob/master/lib/tasks/search.rake#L14)):

```bash
bin/rake search:rebuild_index
```

## Hacking

While hacking on this or testing functionality, there are a few things you can do to
make this easier to use.

#### Skip file writing
```bash
# If you set this env var to any value, the scripts will not write a result file 
export SKIP_USERNAME_JSON_FILE_WRITE=1
# Unset it to re-enable result file writing
unset SKIP_USERNAME_JSON_FILE_WRITE
```

#### Use arbitrary JSON instead of file contents
```bash
# Assuming you are testing the edX Django User username updates...
unset XPRO_RESULT_JSON_FILENAME
export XPRO_RESULT_JSON_VALUE='{"updated": [{"old_username": "01DN2M6WDR8E5MHPGE12NX4JZ2", "new_username": "my-new-username"}]}'
# The script will parse the above value instead of looking for the JSON in a file
make -f $UPDATE_REPO_PATH/Makefile run.edx

# To test edX forum username updates, just change the env var names...
unset EDX_RESULT_JSON_FILENAME
export EDX_RESULT_JSON_VALUE='{}'
# ...
```
