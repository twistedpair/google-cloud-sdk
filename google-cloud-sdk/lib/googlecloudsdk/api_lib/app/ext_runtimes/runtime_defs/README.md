
This directory contains the runtime definitions for the core supported
runtimes, one per subdirectory.  These are to be imported from their canonical
repositories on github.

These directories may contain python files, but they are not imported by the
interpreter running gcloud.  Instead, gcloud invokes the scripts contained in
these directories by spawning a new interpreter.
