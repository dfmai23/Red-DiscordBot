For /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a.%%b)
start_launcher.bat 2>&1 | tee "log\log_%date%_%mytime%.txt"