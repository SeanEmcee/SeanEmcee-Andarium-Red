// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import CryptoKit

/// Installs pre-bundled, individually SHA-256-pinned APKs after the real Android 17 guest boots.
/// No Android image modification is required for *ordinary user applications*.
/// This does not grant root or signature-level clipboard privileges.
nonisolated enum RedGuestApkInstaller {
    struct Package: Sendable, Equatable {
        let filename: String
        let androidPackage: String
        let expectedBytes: Int64
        let expectedSHA256: String
    }

    /// The two release artifacts have identities taken from GitHub release metadata.
    /// Custom launcher/clipboard APKs are not bundled until independently built and pinned.
    static let official: [Package] = [
        Package(filename: "Magisk-v31.1.apk", androidPackage: "com.topjohnwu.magisk",
                expectedBytes: 10_679_283,
                expectedSHA256: "89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7"),
        Package(filename: "Titanium-v157.apk", androidPackage: "io.github.jqssun.helium",
                expectedBytes: 335_631_810,
                expectedSHA256: "c65ef275124058617b2cf0dcc3989b143e74b32ca5a43d9279a0edece8fe7051"),
        Package(filename: "AppManager-v4.1.1.apk", androidPackage: "io.github.muntashirakon.AppManager",
                expectedBytes: 28_270_163,
                expectedSHA256: "2540d6d9352acd8b04d6210140630a380abb1bc46ad4745c89ad97603dee3c40"),
        Package(filename: "Termux-v0.118.3-arm64.apk", androidPackage: "com.termux",
                expectedBytes: 35_106_607,
                expectedSHA256: "72fdb596045116bf5ba1b5bdf5b26fddb9acc0bd074ad9f2da9eb0ae85e83a4e"),
        Package(filename: "HeliBoard-v4.2-release.apk", androidPackage: "helium314.keyboard",
                expectedBytes: 22_431_797,
                expectedSHA256: "69b2b2fb349934371b1ed2d3569541cc0bda987f8aaf5eb5f5b157961f76de86"),
        Package(filename: "FDroid-v2.0.1.apk", androidPackage: "org.fdroid.fdroid",
                expectedBytes: 12_537_183,
                expectedSHA256: "83d3fe522281c3cb89fce3bc05038f81b3c3b32c108536941f184c5f9bb53778"),
    ]

    // Build-time generated entries for user-built, hash-verified launcher APKs.
    static let custom: [Package] = [
        // RED_CUSTOM_PACKAGES
    ]
    static let packages: [Package] = official + custom

    enum PackageError: Error, LocalizedError {
        case notBundled(String)
        case wrongSize(String)
        case wrongDigest(String)
        case unreadable(String)
        var errorDescription: String? {
            switch self {
            case .notBundled(let name): return "APK is not in the app bundle: \(name)"
            case .wrongSize(let name): return "APK size mismatch: \(name)"
            case .wrongDigest(let name): return "APK signature/digest mismatch: \(name)"
            case .unreadable(let name): return "Unable to read APK: \(name)"
            }
        }
    }

    static func bundledURL(for package: Package, in bundle: Bundle = .main) -> URL? {
        let name = String(package.filename.dropLast(4))
        return bundle.url(forResource: name, withExtension: "apk", subdirectory: "RedBundledAPKs")
            ?? bundle.url(forResource: name, withExtension: "apk")
    }

    /// Streaming hash: Titanium is ~335 MiB, so never load the entire file into RAM.
    static func verifiedURL(for package: Package, in bundle: Bundle = .main) throws -> URL {
        guard let url = bundledURL(for: package, in: bundle) else {
            throw PackageError.notBundled(package.filename)
        }
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        let size = (attributes[.size] as? NSNumber)?.int64Value ?? -1
        guard size == package.expectedBytes else { throw PackageError.wrongSize(package.filename) }
        guard let file = try? FileHandle(forReadingFrom: url) else { throw PackageError.unreadable(package.filename) }
        defer { try? file.close() }
        var hasher = SHA256()
        do {
            while let piece = try file.read(upToCount: 1024 * 1024), !piece.isEmpty {
                hasher.update(data: piece)
            }
        } catch { throw PackageError.unreadable(package.filename) }
        let actual = hasher.finalize().map { String(format: "%02x", $0) }.joined()
        guard actual == package.expectedSHA256 else { throw PackageError.wrongDigest(package.filename) }
        return url
    }
}
