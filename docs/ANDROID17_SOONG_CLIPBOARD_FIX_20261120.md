# Andarium Red — Android 17 Soong clipboard compatibility

Build [44803035750](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44803035750)
completed the pinned source checkout and the verified low-memory Soong host
bootstrap, but its Android.bp graph generation produced the first genuine
source error:

```
device/kernarium/andarium/twoyi-red/clipboard/Android.bp:3:1:
module "TwoyiRedClipboard" variant "android_common":
sdk_version: sdk_version must have a value when the module is located at
vendor or product (if PRODUCT_ENFORCE_PRODUCT_PARTITION_INTERFACE is set).
```

The reviewed LineageOS24 Soong revision
`a528a88bd553d2a449ad9338a3e944b89a164971`, Java
`base.go`, applies `checkSdkVersions` to product modules and
`checkPlatformAPI` to reject an app that declares both
`sdk_version` and `platform_apis: true`.

The clipboard app has only SDK/system SDK imports. Its product-partition
placement, privileged flag, platform certificate, manifest and Java provider
are all retained. The corrected `guest_clipboard/Android.bp` declares
`sdk_version: "system_current"` and omits `platform_apis`.

An independent cheap GitHub Actions test validates module policy and runs
the existing clipboard unit tests. This does not prove the full Android
image compiles; it prevents retrying the same known Soong property error.
The original verified kernel, Kernarium, accessibility and Git object caches
are reused unchanged.
