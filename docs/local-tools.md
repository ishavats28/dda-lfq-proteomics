# Local scientific tools

Scientific executables are configured by path and stored under the ignored `.local/tools/` directory. They are never redistributed with this project.

## MSFragger 4.4.1

MSFragger has a separate academic/non-commercial license. Obtain the official distribution only through `https://msfragger-upgrader.nesvilab.org/upgrader/`, completing any required email or license-acceptance step. Do not copy the JAR into version-controlled content.

Extract the official 4.4.1 distribution so that the JAR is located at a path such as:

```text
.local/tools/msfragger/MSFragger-4.4.1.jar
```

Then configure `--msfragger_jar` with that local path. The workflow verifies the detected version before searching. Raw-vendor support may also require the distribution's `ext` directory, but the baseline workflow accepts mzML and does not require vendor libraries.

## Philosopher 5.1.0

The expected standalone Linux amd64 executable is installed from the official release archive at `https://github.com/Nesvilab/philosopher/releases/tag/v5.1.0`. Configure `--philosopher_bin` with the local executable path. The supported `philosopher version` command is used for validation.

No user-specific license files, credentials, executables, archives, or absolute local paths belong in repository-facing files.
