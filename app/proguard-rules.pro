# Models (Gson / Retrofit)
-keep class com.smarttravel.data.model.** { *; }
-keepattributes Signature
-keepattributes *Annotation*
-keepattributes EnclosingMethod
-keepattributes InnerClasses

# Gson
-keep class com.google.gson.** { *; }
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Retrofit
-keepattributes RuntimeVisibleAnnotations, RuntimeInvisibleAnnotations, RuntimeVisibleParameterAnnotations, RuntimeInvisibleParameterAnnotations, AnnotationDefault
-keepclassmembers,allowshrinking,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}
-dontwarn org.codehaus.mojo.animal_sniffer.IgnoreJRERequirement
-dontwarn javax.annotation.**
-dontwarn kotlin.Unit
-dontwarn retrofit2.KotlinExtensions
-dontwarn retrofit2.KotlinExtensions$*

# OkHttp
-dontwarn okhttp3.internal.platform.**
-dontwarn org.conscrypt.**

# Glide
-keep public class * implements com.bumptech.glide.module.GlideModule
-keep class * extends com.bumptech.glide.module.AppGlideModule { <init>(...); }
-keep public enum com.bumptech.glide.load.ImageHeaderParser$** {
    **[] $VALUES;
    public *;
}
-keep class com.bumptech.glide.load.data.ParcelFileDescriptorRewinder$InternalRewinder {
    *** rewind();
}

# OSMDroid / maps
-keep class org.osmdroid.** { *; }
-dontwarn org.osmdroid.**

# Google AI (Generative)
-keep class com.google.ai.** { *; }
-keep class com.google.common.** { *; }
-dontwarn com.google.j2objc.annotations.**

# EncryptedSharedPreferences / Tink
-keep class androidx.security.crypto.** { *; }
-dontwarn com.google.crypto.tink.**

# Parcelable / navigation safe args (if used)
-keepclassmembers class * implements android.os.Parcelable {
    public static final ** CREATOR;
}
