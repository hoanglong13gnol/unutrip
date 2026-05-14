@rem Gradle startup script for Windows
@if "%DEBUG%"=="" @echo off
@setlocal
if "%JAVA_EXE%"=="" set "JAVA_EXE=java"
set CLASSPATH=%~dp0\gradle\wrapper\gradle-wrapper.jar
"%JAVA_EXE%" -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*
:end
@endlocal
