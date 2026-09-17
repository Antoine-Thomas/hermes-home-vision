
# Liste des tâches à corriger et nouvelle fréquence
$tasks = @(
    @{ name = "\SecurityMonitoring-AlertBridge";  freq = "5";   script = "C:\Users\searc\AppData\Local\hermes\data\security-monitoring\telegram\alert_bridge.py" },
    @{ name = "\SecurityMonitoring-LogMonitor";   freq = "10";  script = "C:\Users\searc\AppData\Local\hermes\data\security-monitoring\monitors\log_monitor.py --telegram" },
    @{ name = "\SecurityMonitoring-PortMonitor";  freq = "10";  script = "C:\Users\searc\AppData\Local\hermes\data\security-monitoring\monitors\port_monitor.py --telegram" },
    @{ name = "\SecurityMonitoring-UpdateChecker"; freq = "60"; script = "C:\Users\searc\AppData\Local\hermes\data\security-monitoring\update_checker.py" }
)

foreach ($t in $tasks) {
    $vbsPath = "C:\Users\searc\AppData\Local\hermes\scripts\hidden_$(($t.name -replace '\\', '')).vbs"
    
    # Créer le wrapper VBS pour lancer python masqué
    $vbsContent = @"
Set sh = CreateObject("WScript.Shell")
sh.Run "C:\Users\searc\AppData\Local\Programs\Python\Python310\python.exe $($t.script)", 0, False
"@
    $vbsContent | Out-File -FilePath $vbsPath -Encoding ascii
    
    # Mettre à jour la tâche pour pointer vers le VBS
    # Note: On passe la fréquence ici via /sc minute /mo
    $action = "schtasks /change /tn `"$($t.name)`" /tr `"wscript.exe //B `"$vbsPath`"`" /sc minute /mo $($t.freq)"
    Write-Host "Execution: $action"
    Invoke-Expression $action
}
