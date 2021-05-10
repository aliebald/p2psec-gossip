# Gossip

# Config

The following settings can be adjusted in the `config.ini` file in the root directory

- `cache_size`: _TODO Documentation_
- `max_connections`: _TODO Documentation_
- `bootstrapper`: _TODO Documentation_
- `p2p_address`: _TODO Documentation_
- `api_address`: _TODO Documentation_

# Git Workflow

We currently follow the workflow described in the specification. The following summarizes this workflow and helpful commands.

## Commands

- `git branch`: shows available branches and highlights the current branch

## Workflow

In the following steps, replace `<working_branch>` with the name of your branch.

### Step 1 & 2

- Commit your work only to your personal branch, named after your last name. 

### Step 3:
- `git checkout master`
- `git pull origin <working_branch>` 

### Step 4:
- `git checkout <working_branch>`
- `git rebase master`

### Step 5:
- `git checkout master`
- `git merge <working_branch>`

### Step 6:
- `git push`
- `git checkout <working_branch>`
