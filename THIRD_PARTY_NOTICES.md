# Third-party components

Veil's original app code is provided under the included MIT license. Beta Blocker is a separate product by Isla2D; none of its software or artwork is included.

## NudeNet 3.4.2 / 320n

Author: BEDAPUDI PRANEETH. Source: https://pypi.org/project/nudenet/3.4.2/

The model is obtained only by the build script from the exact published wheel:
`nudenet-3.4.2-py3-none-any.whl`

SHA-256: `5937dbd84e5d8e5de038f08ffea5a1bb50a08475776bf2b4795914ce0eaf0331`

PyPI describes this release as MIT. The script preserves the upstream license from the wheel as `app/src/main/assets/NUDENET-LICENSE.txt`, along with provenance and the model's own checksum. Model bytes and that extracted notice are not tracked in the repository until this download runs. Keep upstream notices with redistributed builds; consult upstream terms for the weights before any commercial distribution.

## ONNX Runtime 1.21.0

Microsoft and contributors. MIT license. Android runtime resolved through Maven Central as `com.microsoft.onnxruntime:onnxruntime-android:1.21.0`.

Source and notices: https://github.com/microsoft/onnxruntime/tree/v1.21.0

## Build tools

Android Gradle Plugin, Android SDK and Gradle have their own licenses. The build uses official distributions/repositories; SDK and Gradle distribution binaries are downloaded during setup.

The standard `gradlew`, `gradlew.bat` and `gradle/wrapper/gradle-wrapper.jar` are included from [Gradle v8.11.1](https://github.com/gradle/gradle/tree/v8.11.1). The wrapper JAR SHA-256 is `2db75c40782f5e8ba1fc278a5574bab070adccb2d21ca5a6e5ed840888448046`. Upstream licensing is preserved in [licenses/gradle-LICENSE.txt](licenses/gradle-LICENSE.txt). The wrapper properties pin both Gradle 8.11.1 and its distribution checksum.
