plugins {
    id("com.android.application")
}

android {
    namespace = "com.mikeapple.myapplication"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.mikeapple.myapplication"
        minSdk = 7
        targetSdk = 7
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_7
        targetCompatibility = JavaVersion.VERSION_1_7
    }
}

dependencies {
}