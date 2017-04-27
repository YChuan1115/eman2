try:
    import mpi
except:
    print "import error: mpi"
    import sys
    for p in sys.path:
        print p
