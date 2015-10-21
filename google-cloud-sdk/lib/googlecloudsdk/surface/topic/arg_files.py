# Copyright 2015 Google Inc. All Rights Reserved.

"""Gcloud test argument files supplementary help."""

from googlecloudsdk.calliope import base


class TestingArgFiles(base.Command):
  """Supplementary help for arg-files to be used with *gcloud test*."""

  def Run(self, args):
    self.cli.Execute(args.command_path[1:] + ['--document=style=topic'])
    return None

  detailed_help = {

      'DESCRIPTION': """\
          {description}

          All *gcloud test android run* arguments may be specified by flags on
          the command line and/or via a YAML-formatted _ARG_FILE_. The optional,
          positional ARG_SPEC argument on the command line is used to specify
          a single _ARG_FILE_:_ARG_GROUP_NAME_ pair, where _ARG_FILE_ is the
          path to the YAML argument file, and _ARG_GROUP_NAME_ is the name
          of the argument group to load and parse. The _ARG_FILE_ must
          contain valid YAML syntax or gcloud will respond with an error.

          The basic format of a YAML argument file is:

            arg-group1:
              arg1: value1  # a comment
              arg2: value2
              ...

            # Another comment
            arg-group2:
              arg3: value3
              ...

          List arguments may be specified within square brackets:

            device-ids: [Nexus5, Nexus6, Nexus9]

          or by using the alternate YAML list notation with one dash per list
          item:

            ```
            device-ids:
              - Nexus5
              - Nexus6
              - Nexus9
            ```

          If a list argument only contains a single value, you may omit the
          square brackets:

            device-ids: Nexus9

          Note that while the command-line flags support both singular and
          plural forms of each list-style argument (e.g. either --device-id
          or --device-ids), argument files only support the plural forms.

          Composition

          A special *include: [_ARG_GROUP1_, ...]* syntax allows merging or
          composition of argument groups (see *EXAMPLES* below). Included
          argument groups can *include:* other argument groups within the
          same YAML file, with unlimited nesting.

          Precedence

          An argument which appears on the command line has the highest
          precedence and will override the same argument if it is specified
          within an argument file.

          Any argument defined directly within a group will have higher
          precedence than an identical argument which is merged into that
          group using the *include:* keyword.

          """,

      'EXAMPLES': """\

          Here are the contents of a very simple YAML argument file which
          we'll assume is stored in a file named excelsior_args.yaml:

            # Run a quick 'robo' test on the 'Excelsior' app for
            # 90 seconds using only the default virtual device.
            quick-robo-test:
              app: path/to/excelsior.apk
              type: robo
              max-steps: 100
              timeout: 90s
              async: true

          To invoke this test, run:

            $ gcloud alpha test android run excelsior_args.yaml:quick-robo-test

          Here is a slightly more complicated example which demonstrates
          composition of argument groups. Assume the following YAML text
          is appended to the arg-file shown above named excelsior_args.yaml:

            # Specify some unit tests to be run against a test matrix
            # with one device type, two Android versions, and four
            # locales, for a total of eight test variations (1*2*4).
            unit-tests:
              type: instrumentation
              app: path/to/excelsior.apk
              test: path/to/excelsior-test.apk  # the unit tests
              timeout: 10m
              device-ids: Nexus6
              include: [supported-versions, supported-locales]

            supported-versions:
              os-version-ids: [21, 22]

            supported-locales:
              locales: [en, es, fr, it]

          To invoke this test matrix, run:

            $ gcloud alpha test android run excelsior_args.yaml:unit-tests

          To run these unit tests with the same locales and os-version-ids,
          but substituting a sampling of three physical Android devices
          instead of the single virtual Nexus6 device, run:

            $ gcloud alpha test android run excelsior2.args:unit-tests\
 --device-ids shamu,m7,g3

          In the last example, the --device-ids argument on the
          command line overrides the device-ids: specification inside the
          arg-file because command-line arguments have higher precedence.

          """,
      }
