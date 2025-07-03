# Documentation

## How do you build container images?

- Dockerfile
    - BuildKit
    - Buildx
- Ko/Jib etc.
- Kaniko
- Buildpacks
- Bazel
- Apko

## Essential Build Dependencies

### Go

- `busybox` - Provides essential Unix utilities like `sh`, `ls`, `mkdir`, `ln`, etc.
- `ca-certificates-bundle` - SSL/TLS certificates for secure connections when downloading Go modules
- `git` - Required for git rev-parse HEAD command in the build script and Go module downloads
- `make` - Build tool (though not directly used in this pipeline, often needed for Go projects)
- `bash` - Better shell for running complex build scripts
- `coreutils` - Provides date, head, rev, cut commands used in the build
- `findutils` - Provides find command
- `grep` - Text searching utility
- `sed` - Stream editor for text manipulation
- `gawk` - AWK text processing tool
