# strace results
# grep execve topo-test.tr returns one line corresponding to executing pytest


import os
import sys
import zlib


class CommitNode:
    def __init__(self, commit_hash, branches=[]):
        self.commit_hash = commit_hash
        self.parents = set()
        self.children = set()
        self.branches = branches


# gets directory where .git exists or else exits if not exists
def get_git_directory():
    # get current directory
    current_dir = os.getcwd()
    is_git_exists = False
    # search recursively going up the parent directories till root is reached
    while current_dir != '/':
        check_git_dir = current_dir + '/.git'
        is_git_exists = os.path.exists(check_git_dir)
        if is_git_exists:
            return current_dir
        else:
            current_dir = os.path.dirname(current_dir)
    sys.stderr.write('Not inside a Git repository\n')
    exit(1)


# creates a dictionary to hold the branch hash and associated branch names
def create_branch_dict():
    # initialize
    branch_dict = {}
    # change dir to read the branch hashes
    os.chdir('./refs/heads')
    for root, directories, files in os.walk("."):
        for name in files + directories:
            if os.path.isfile(os.path.join(root, name)):
                # file names are in format ./<name> so get string after 2 chr
                branch_name = os.path.join(root, name)[2:]
                commit_hash = (open(branch_name).read()).strip()
                # if commit hash does not exist in the dict, add it
                if commit_hash not in branch_dict.keys():
                    branch_dict[commit_hash] = [branch_name]
                else:
                    branch_dict[commit_hash].append(branch_name)
    # change directory back to the .git directory
    os.chdir('../../')
    return branch_dict


# gets parent hash after decompressing file in objects dir
def get_parents(commit_hash):
    dir = commit_hash[0:2]
    file = commit_hash[2:]
    os.chdir(os.path.join('.', dir))
    compr_contents = open(file, 'rb').read()
    lines = zlib.decompress(compr_contents).decode()
    os.chdir('../')
    parents = []
    for line in lines.split('\n'):
        if line.startswith('parent'):
            parents.append(line[7:])
    return parents


# creates a dictionary to hold all nodes in the graph
# also returns the root_commits
def create_graph_dict(branch_dict):
    # change dir to objects to read the parent info
    os.chdir('./objects')
    # initialize graph dictionary
    node_dict = {}
    root_commits = set()
    # loop through each hash in branch_dict which contains
    # each branch hash and branch names list
    for hash in branch_dict:
        if hash in node_dict.keys():
            node_dict[hash].branches = branch_dict[hash]
        else:
            node_dict[hash] = CommitNode(hash, branch_dict[hash])
            stack = [node_dict[hash]]
            while len(stack) != 0:
                node = stack.pop()
                # get the parent hashes from ./objects files
                parent_hashes = get_parents(node.commit_hash)
                if len(parent_hashes) == 0:
                    root_commits.add(node.commit_hash)
                for parent_h in parent_hashes:
                    if parent_h not in node_dict.keys():
                        node_dict[parent_h] = CommitNode(parent_h)
                    # Add current node as child to parent
                    node_dict[parent_h].children.add(node)
                    # Add this parent to current node
                    node.parents.add(node_dict[parent_h])
                    stack.append(node_dict[parent_h])
    os.chdir('../')
    return list(root_commits), node_dict


# topological sort with result in a List
def topo_sort(root_commits, node_dict):
    res, scn, stack = [], set(), root_commits.copy()
    # stack used as recursion
    while len(stack) != 0:
        top = stack[-1]
        scn.add(top)
        children = [n for n in node_dict[top].children if n.commit_hash not in scn]
        # when no more children stop and add to result list
        if len(children) == 0:
            stack.pop()
            res.append(top)
        else:
            stack.append(children[0].commit_hash)
    return res


def topo_order_commits():
    git_dir = get_git_directory() + '/.git'
    os.chdir(git_dir)
    branch_dict = create_branch_dict()
    root_commits, node_dict = create_graph_dict(branch_dict)
    res_list = topo_sort(root_commits, node_dict)
    for i in range(len(res_list)):
        cur_nd = node_dict[res_list[i]]
        if len(cur_nd.branches) == 0:
            print(res_list[i])
        else:
            print(res_list[i] + " ", end="")
            print(*sorted(cur_nd.branches))
        # next not parent print sticky
        if i < (len(res_list) - 1):
            next_nd = node_dict[res_list[i + 1]]
            if res_list[i + 1] not in [p.commit_hash for p in cur_nd.parents]:
                print(*[p.commit_hash for p in cur_nd.parents], end="=\n\n=")
                print(*[c.commit_hash for c in next_nd.children])


if __name__ == '__main__':
    topo_order_commits()
