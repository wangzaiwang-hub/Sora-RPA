@echo off
echo 启动 Chrome 并允许访问本地服务器...
echo.
echo 注意：这个 Chrome 实例会禁用某些安全检查
echo 仅用于开发测试，不要用于日常浏览
echo.
echo 正在关闭现有的 Chrome 进程...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

echo 启动新的 Chrome 实例...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --disable-features=BlockInsecurePrivateNetworkRequests ^
  --user-data-dir="%TEMP%\chrome-dev-session" ^
  https://sora.chatgpt.com

echo.
echo Chrome 已启动，请在新窗口中测试
echo.
pause
