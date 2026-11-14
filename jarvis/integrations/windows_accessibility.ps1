param([ValidateSet('focus-start','focus-stop','focus-status','selection')][string]$Action)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$condition = [System.Windows.Automation.Condition]::TrueCondition
$children = [System.Windows.Automation.TreeScope]::Children
$descendants = [System.Windows.Automation.TreeScope]::Descendants

if ($Action -eq 'selection') {
    $title = $env:JARVIS_WINDOW_TITLE
    $windows = @($root.FindAll($children, $condition) | Where-Object {
        $_.Current.Name.IndexOf($title, [StringComparison]::OrdinalIgnoreCase) -ge 0
    })
    if ($windows.Count -ne 1) { throw 'Indica um titulo que identifique uma unica janela.' }
    $textPattern = [System.Windows.Automation.TextPattern]::Pattern
    $selections = @()
    foreach ($element in $windows[0].FindAll($descendants, $condition)) {
        $pattern = $null
        if (!$element.TryGetCurrentPattern($textPattern, [ref]$pattern)) { continue }
        foreach ($range in $pattern.GetSelection()) {
            $text = $range.GetText(4001)
            if (!$text) { continue }
            $selections += $text.Substring(0, [Math]::Min($text.Length, 4000))
        }
    }
    $selections | Select-Object -Unique
    exit
}

function Find-FocusButton([string]$id) {
    $automationId = [System.Windows.Automation.AutomationElement]::AutomationIdProperty
    $search = New-Object System.Windows.Automation.PropertyCondition($automationId, $id)
    foreach ($window in $root.FindAll($children, $condition)) {
        if ($window.Current.ClassName -ne 'ApplicationFrameWindow') { continue }
        $button = $window.FindFirst($descendants, $search)
        if ($button -and $button.Current.IsEnabled) { return $button }
    }
}
Start-Process 'ms-settings:quiethours'
$expected = if ($Action -eq 'focus-stop') { 'focusStartButton' } else { 'focusStopButton' }
$trigger = if ($Action -eq 'focus-stop') { 'focusStopButton' } else { 'focusStartButton' }
$invoked = $false
for ($attempt = 0; $attempt -lt 25; $attempt++) {
    if ($Action -eq 'focus-status') {
        if (Find-FocusButton 'focusStopButton') { 'active'; exit }
        if (Find-FocusButton 'focusStartButton') { 'inactive'; exit }
    } elseif (Find-FocusButton $expected) {
        if ($Action -eq 'focus-stop') { 'inactive' } else { 'active' }
        exit
    } elseif (!$invoked) {
        $button = Find-FocusButton $trigger
        if ($button) {
            $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            $invoked = $true
        }
    }
    Start-Sleep -Milliseconds 200
}
throw 'Nao foi possivel confirmar o estado da concentracao do Windows.'
