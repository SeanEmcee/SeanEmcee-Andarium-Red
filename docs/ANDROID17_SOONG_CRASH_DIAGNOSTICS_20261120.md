# Andarium Red free GitHub runner: persistent Soong failure diagnostics

Run [44832888245](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44832888245)
completed all kernel, source, patch and extra-swap steps but failed inside
the Android compiler. GitHub's raw job log returned BlobNotFound and the final
diagnostic artifact step was skipped, so the *specific* error and whether OOM
occurred are not yet proven.

The standalone [44860422491](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44860422491)
GitHub Checks API test succeeded: it created a completed, neutral check,
updated its output and retained the latest diagnostic snapshot.

The compiler job now creates one neutral check and updates it roughly every
135 seconds with the latest bounded and redacted compiler log tail and RAM,
swap and filesystem readings. The GitHub token has only the narrowly scoped
contents read, actions read and checks write permissions. Telemetry network
failure never aborts compilation. It contains no fake ROM artifacts, and no
source file or original immutable cache is modified.

The Soong host Go memory soft target was also lowered from 6 GiB to
4.5 GiB with more aggressive Go collection (GOGC 8) to test a plausible
hosted-memory-pressure hypothesis. This is a mitigation, not evidence
that the prior run failed from OOM. The exact pinned upstream, reviewed
patches and build-graph validation remain mandatory. A successful smoke
test only validates the instrumentation; a genuine Android image remains
unproven until compiled and independently verified.
