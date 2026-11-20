# Andarium Red Android 17: free GitHub build recovery

The November 20 GitHub build #44762851230 failed inside its compile step
after successful source sync, cache restore, kernel/accessibility verification,
and swap setup. Its job-log download returned GitHub BlobNotFound (HTTP 404)
and no compiled ROM artifact was uploaded. Do not claim a specific compiler
error or memory condition for that run without its actual log.

The original pinned Kernarium producer runs a complete source integrity check
both before compilation and after its target-files packaging. A temporary
host-only Go memory patch must be applied *after* the first verifier and
reverted *before* the last verifier. Previously the host Go modification
remained until EXIT, guaranteeing a final dirty-source verification failure
if the Android compilation completed. The new derived producer restores
the original Soong file before this final check; its EXIT trap remains as a
failure cleanup only.

Verification first runs a small fixture, then restores the exact pinned
Kernarium checkout from the existing cache and tests the actual unchanged
vendor script. The host executable Go policy is still experimental, and
success on the fixture does not prove the complete Android 17 build will fit.

Each full build now writes a bounded 16 MB tail of compiler output and
periodic RAM/swap/disk usage to a diagnostic GitHub Actions artifact, to
make future failures inspectable even when the normal job-log redirect
breaks. A runner-level abrupt shutdown may still prevent artifact upload.
No source-integrity checks are disabled; no synthetic image is published.
