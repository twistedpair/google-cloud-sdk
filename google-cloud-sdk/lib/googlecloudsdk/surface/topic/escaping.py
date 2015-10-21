# Copyright 2015 Google Inc. All Rights Reserved.

"""Resource escaping supplementary help."""

from googlecloudsdk.calliope import base


# NOTE: If the name of this topic is modified, please make sure to update all
# references to it in error messages and other help messages as there are no
# tests to catch such changes.
class Escaping(base.Command):
  """List/dictionary-type argument escaping supplementary help."""

  def Run(self, args):
    self.cli.Execute(args.command_path[1:] + ['--document=style=topic'])
    return None

  detailed_help = {

      'DESCRIPTION': """\
          {description}

          *gcloud* supports list-type and dictionary-type flags that take one
          argument which is a list of one or more comma-separated items:

              --list-flag=value1,value2,value3

              --dict-flag=key1=value1,key2=value2

          In the case of a dict-type flag, each item is a key-value pair
          separated by '='. If more than one '=' is present, the first is used.

          In order to include commas in your arguments, specify an alternate
          delimiter using the following syntax:

              ^DELIM^flag value, with comma

          where _DELIM_ is a sequence of one or more characters that may not
          appear in any value in the list.

          """,

      'EXAMPLES': """\
          In these examples, a list-type or dictionary-type flag is given, along
          with a shell comment explaining how it is parsed. The parsed flags are
          shown here using Python-style list or dict formats (in other
          languages, what Python calls "dicts" are often called "associative
          arrays," "maps," or "hashes").

          Basic example:

              --list-flag=^:^a,b:c,d # => ['a,b', 'c,d']

          Multi-character delimiters are allowed:

              --list-flag=^--^a-,b--c # => ['a-,b', 'c']

          Just one '^' has no special meaning:

              --list-flag=^a,b,c # => ['^a', 'b', 'c']

          This is an alternative way of starting with '^':

              --list-flag=^,^^a,b,c # => ['^a', 'b', 'c']

          A '^' anywhere but the start has no special meaning:

              --list-flag=a^:^,b,c # => ['a^:^', 'b', 'c']

          Dictionary-type arguments work exactly the same as list-type
          arguments:

              --dict-flag=^:^a=b,c:d=f,g # => {'a: 'b,c', 'd': 'f,g'}
          """,
      }
