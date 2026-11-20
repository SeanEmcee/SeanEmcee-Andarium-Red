# Android 17 source synchronization recovery

The November 20 run #44783288289 failed before Soong. Official Repo
reported it could not initialize the working tree for the pinned
prebuilts/module_sdk/ConfigInfrastructure project. Upstream Repo's
error is emitted after a failed Git read-tree checkout; the summary
alone does not prove whether the failure was transient networking,
missing Git objects, disk space or a filesystem conflict.

The original Kernarium source preparer is immutable and pinned to
fbe12ee72d195f0241c4fc24090a98b259026604. A checked, temporary
sibling derivative changes ONLY the repo sync step after manifest pinning.
It first checks out the previously failing project with one worker
(with one retry). Then it syncs the full pinned tree with --fail-fast;
one single-worker retry uses previously downloaded Git objects if
the first sync fails. Neither checkout is forced, skipped or re-pointed.

The complete original source patch, Mesa and accessibility verification
still runs after source synchronization. On a failure, a bounded tail of
the source log, source-derivative audit and status are uploaded under
a normal visible diagnostics directory. The kernel, Kernarium,
accessibility and existing Git-object caches are not replaced.

A cheap GitHub Actions smoke test must validate the exact pinned
producer script before the next full Android sync. The source cache
is only a subset of the entire Android tree; reruns still fetch
missing projects.
