Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\My Projects\Personal Projects\Prime"
WshShell.Run "cmd.exe /k title Prime AI Cockpit && ""C:\Users\thora\AppData\Local\Programs\Python\Python312\python.exe"" ""c:\My Projects\Personal Projects\Prime\prime.py"" --force", 1, False
