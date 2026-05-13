@rem Gradle startup script for Windows
@if "%DEBUG%"=="" @echo off
@setlocal
set CLASSPATH=%~dp0\gradle\wrapper\gradle-wrapper.jar
"%JAVA_EXE%" -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*
:end
@endlocal
