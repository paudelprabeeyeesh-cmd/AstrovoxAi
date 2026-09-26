// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AstrovoxAI",
    platforms: [
        .iOS(.v16),
        .macOS(.v13)
    ],
    products: [
        .library(name: "AstrovoxAI", targets: ["AstrovoxAI"])
    ],
    targets: [
        .target(
            name: "AstrovoxAI",
            dependencies: []
        ),
        .testTarget(name: "AstrovoxAITests", dependencies: ["AstrovoxAI"])
    ]
)
