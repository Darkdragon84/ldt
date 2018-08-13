import json
import sys
import random

import ruamel.yaml as yaml

from hurry.filesize import size

from ldt.helpers.exceptions import ResourceError as ResourceError

def get_object_size(obj, seen=None):
    '''

    A function that recursively finds size of objects,
    from https://goshippo.com/blog/measure-real-size-any-python-object/
    Object sizes in Python should really not be that hard.

    Warning: loading the same file into memory may result in slightly
    different object sizes.

    Args:
        obj: the object for which the size is to be calculated
        seen: helper variable

    Returns:
        (int): the size of the object in bytes.

    '''

    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_object_size(v, seen) for v in obj.values()])
        size += sum([get_object_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_object_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_object_size(i, seen) for i in obj])
    return size



#todo add lowercasing
def load_resource(path, format="infer", lowercasing=True):
    """

    A helper function for loading various files formats, optionally
    lowercasing them, and displaying the sizes of the resulting objects
    (for monitoring huge resources).

    Args:
        path (str): path to file with the resource
        format (str): the format of the file. By default it is inderred from
            the file extension, but can also be specified directly. The
            following formats are supported:

                :type freqdict: for tab-separated [Word <tab> Number] file
                :type csv_dict: for [Word1 <tab> Word2,Word3,Word4...] or [Word1 <tab> Word2]
                :type vocab: for one-word-per-line vocab file
                :type json: a json dictionary
                :type yaml: a yaml dictionary

    Returns:
        (set, dict): a set object for vocab files, a dictionary for
            everything else
    """

    if format == "infer":
        format = path.split(".")[-1]
    no_message=False

    if format in ["freqdict", "tsv_dict", "json", "yaml"]:

        res = {}

        if format == "freqdict":
            with open(path, "r", encoding="utf8") as f:
                for line in f:
                    print(line)
                    line = line.strip().split("\t")
                    try:
                        res[line[0]] = int(line[1])
                    except IndexError:
                        print("Wrong file format. [Word <tab> Number] per line expected.")

                        break
            print(res)

        if format == "tsv_dict":
            with open(path, "r", encoding="utf8") as f:
                # figure out whether it's a list or one-word entry format

                lines = f.readlines()

            commas_present = 0
            for line in lines[:5]:
                line = line.strip().split("\t")
                try:
                    commas = line[1].count(",")
                except IndexError:
                    print("Wrong file format. [Word1 <tab> Word2] or ["
                          "Word1 <tab> Word2, Word3,Word4...] per line  "
                          "expected.")
                    break
                if commas > 0:
                    commas_present += 1

            if commas_present > 3:

                for line in lines:
                    try:
                        line = line.strip().split("\t")
                        words = line[1].split(",")
                        res[str(line[0])] = set(words)
                    except IndexError:
                        print("Wrong file format. [Word1 <tab> Word2] or ["
                              "Word1 <tab> Word2, Word3,Word4...] per line  "
                              "expected.")
                        break

            else:
                for line in lines:
                    try:
                        line = line.strip().split("\t")
                        res[str(line[0])] = str(line[1])
                    except IndexError:
                        print("Wrong file format. [Word1 <tab> Word2] or ["
                              "Word1 <tab> Word2, Word3,Word4...] per line "
                              "expected.")
                        break

        if format == "json":
            with open(path, "r", encoding="utf8") as f:
                res = json.load(f)

        if format == "yaml":
            # # res = yaml.load(open(path))
            # yaml = YAML(typ='safe')
            with open(path) as stream:
                try:
                    res = yaml.safe_load(stream)
                except yaml.YAMLError:
                    raise ResourceError(
                        "Something is wrong with the .yaml file "
                        "for this language.")
                if "cu" in res:
                    if res["cu"] == "Old Church Slavonic":
                        no_message=True

        if lowercasing:

            # test if the dict keys are lists or not
            random_key = random.choice(list(res))
            if type(res[random_key]) != str:

                new_res = {}
                for k in res.keys():
                    l = str(k).lower()
                    if format != "freqdict":
                        if not l in new_res.keys():
                            new_res[l] = set(str(w).lower() for w in res[k])
                        else:
                            for w in res[k]:
                                new_res[l].add(str(w))
                    else:
                        #if lowercasing a frequency dictionary, add the
                        # frequencies for any merged words
                        if l in new_res:
                            total_frequency = res[k] + res[l]
                            new_res[l] = total_frequency
                        else:
                            new_res[l] = res[k]
                res = new_res

            else:
                res = dict((str(k).lower(), str(v).lower()) for k, v in
                     res.items())

    elif format == "vocab":
        with open(path, "r", encoding="utf8") as f:
            res = f.read().splitlines()
        if lowercasing:
            res = [x.lower() for x in res]
        res = frozenset(res)

    else:
        print("Unknown format. The following formats are supported: \n"
              "* [freqdict] for tab-separated [Word <tab> Number] files;\n"
              "* [tsv_dict] for [Word1 <tab> Word2,Word3,Word4...] or [Word1 <tab> Word2];\n"
              "* [json] for json dictionaries;\n"
              "* [yaml] for yaml dictionaries;\n"        
              "* [vocab] for one-word-per-line vocab files.\n")
        return None

    if len(res) > 0:
        if not no_message:
            print(path, " loaded as ", size(get_object_size(res)))
        return res

    else:
        return None