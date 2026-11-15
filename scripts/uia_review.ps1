$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
try {
    Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
    $job = $env:JARVIS_UIA_REQUEST | ConvertFrom-Json
    $class = [System.Windows.Automation.AutomationElement]
    $scope = [System.Windows.Automation.TreeScope]
    $styles = [System.Windows.Automation.PropertyCondition]

    function Find-Window($title, $processName) {
        $filter = $styles::new($class::NameProperty, [string]$title)
        $windows = @($class::RootElement.FindAll($scope::Children, $filter) | Where-Object {
            $app = Get-Process -Id $_.Current.ProcessId -ErrorAction SilentlyContinue
            $app -and $app.ProcessName -ieq $processName -and -not $_.Current.IsOffscreen
        })
        if ($windows.Count -eq 1) { return $windows[0] }
        if ($windows.Count -gt 1) { throw "Há várias janelas elegíveis com o mesmo título." }
        return $null
    }

    function Find-Control($window, $identifier) {
        if ($null -eq $window) { return $null }
        $filter = $styles::new($class::AutomationIdProperty, [string]$identifier)
        $matches = @($window.FindAll($scope::Descendants, $filter) | Where-Object { -not $_.Current.IsOffscreen })
        if ($matches.Count -eq 1) { return $matches[0] }
        if ($matches.Count -gt 1) { throw "Há vários controlos visíveis com o identificador $identifier." }
        return $null
    }

    $window = Find-Window $job.window $job.process
    if ($null -eq $window) { throw "Não encontrei a janela autorizada." }
    if ($job.type -eq 'navegação') {
        $stepNumber = 0
        foreach ($step in $job.steps) {
            $stepNumber += 1
            $control = Find-Control $window $step.invocar
            $pattern = $null
            if ($null -eq $control -or -not $control.Current.IsEnabled -or
                -not $control.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
                throw "Passo $stepNumber interrompido. O controlo não pode ser aberto."
            }
            $pattern.Invoke()
            $deadline = [DateTime]::UtcNow.AddSeconds(4)
            $found = $false
            while ([DateTime]::UtcNow -lt $deadline) {
                $candidate = Find-Window $job.destination $job.process
                if (Find-Control $candidate $step.esperar) {
                    $window = $candidate
                    $found = $true
                    break
                }
                Start-Sleep -Milliseconds 200
            }
            if (-not $found) { throw "Passo $stepNumber interrompido. O estado esperado não apareceu." }
        }
        @{ estado = "$stepNumber passo(s) confirmado(s)" } | ConvertTo-Json -Compress
    } else {
        $prepared = @()
        foreach ($field in $job.fields) {
            $control = Find-Control $window $field.id
            $pattern = $null
            if ($null -eq $control -or $control.Current.IsPassword -or -not $control.Current.IsEnabled -or
                -not $control.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$pattern) -or
                $pattern.Current.IsReadOnly) { throw "O campo $($field.name) não pode ser preenchido." }
            $prepared += @{ name = $field.name; value = [string]$field.value; pattern = $pattern }
        }
        $checked = @()
        foreach ($field in $prepared) {
            $field.pattern.SetValue($field.value)
            $actual = $field.pattern.Current.Value
            if ($actual -cne $field.value) { throw "O campo $($field.name) ficou com um valor diferente. Revê o formulário." }
            $checked += @{ name = $field.name; value = $actual }
        }
        @{ estado = 'campos preenchidos e relidos para revisão'; campos = @($checked) } | ConvertTo-Json -Depth 4 -Compress
    }
} catch {
    @{ erro = $_.Exception.Message } | ConvertTo-Json -Compress
    exit 1
}
