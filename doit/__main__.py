# lazy way to ignore coverage in this file
if True: # pragma: no cover
    import sys

    from doit.doit_cmd import DoitMain

    sys.exit(DoitMain().run(sys.argv[1:]))

